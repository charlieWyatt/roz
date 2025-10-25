"""
PostgreSQL database client for heatmap data storage and retrieval.
"""

import os
import logging
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseClient:
    """Handles PostgreSQL connections and operations for heatmap data."""

    def __init__(self, host: str, port: int, dbname: str, user: str, password: str,
                 min_conn: int = 1, max_conn: int = 10):
        """
        Initialize database connection pool.

        Args:
            host: Database host
            port: Database port
            dbname: Database name
            user: Database user
            password: Database password
            min_conn: Minimum connections in pool
            max_conn: Maximum connections in pool
        """
        self.conn_params = {
            'host': host,
            'port': port,
            'dbname': dbname,
            'user': user,
            'password': password,
        }

        try:
            self.pool = SimpleConnectionPool(
                min_conn, max_conn, **self.conn_params)
            logger.info(
                f"Database connection pool created: {user}@{host}/{dbname}")
        except psycopg2.Error as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    @contextmanager
    def get_cursor(self, dict_cursor: bool = True):
        """Context manager for database cursors."""
        with self.get_connection() as conn:
            cursor_factory = DictCursor if dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error: {e}")
                raise
            finally:
                cursor.close()

    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                logger.info("Database connection test successful")
                return result is not None
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def insert_heatmap_minute(self, camera_id: str, timestamp: datetime, video_path: str,
                              height: int, width: int, downscale_factor: float,
                              intensity_array: bytes, frame_count: int,
                              total_intensity: float, max_intensity: float,
                              nonzero_pixels: int) -> Optional[int]:
        """
        Insert a heatmap minute record.

        Args:
            camera_id: Camera identifier
            timestamp: Start time of this minute
            video_path: S3 key of source video
            height: Heatmap height
            width: Heatmap width
            downscale_factor: Downscale factor used
            intensity_array: Compressed numpy array bytes
            frame_count: Number of frames processed
            total_intensity: Sum of all intensity values
            max_intensity: Maximum intensity value
            nonzero_pixels: Number of pixels with motion

        Returns:
            Inserted row ID, or None if failed
        """
        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO heatmap_minutes (
                        camera_id, timestamp, video_path, height, width, downscale_factor,
                        intensity_array, frame_count, total_intensity, max_intensity, nonzero_pixels
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (camera_id, timestamp) 
                    DO UPDATE SET
                        video_path = EXCLUDED.video_path,
                        intensity_array = EXCLUDED.intensity_array,
                        frame_count = EXCLUDED.frame_count,
                        total_intensity = EXCLUDED.total_intensity,
                        max_intensity = EXCLUDED.max_intensity,
                        nonzero_pixels = EXCLUDED.nonzero_pixels,
                        processed_at = NOW()
                    RETURNING id
                """, (camera_id, timestamp, video_path, height, width, downscale_factor,
                      intensity_array, frame_count, total_intensity, max_intensity, nonzero_pixels))

                result = cur.fetchone()
                row_id = result['id'] if result else None
                logger.info(
                    f"Inserted heatmap minute: {camera_id} @ {timestamp}")
                return row_id

        except Exception as e:
            logger.error(f"Failed to insert heatmap minute: {e}")
            return None

    def get_heatmap_minutes(self, camera_id: str, start_time: datetime, end_time: datetime,
                            include_arrays: bool = False) -> List[dict]:
        """
        Retrieve heatmap minutes for a time range.

        Args:
            camera_id: Camera identifier
            start_time: Start of time range
            end_time: End of time range
            include_arrays: Whether to include intensity arrays (default: False for performance)

        Returns:
            List of heatmap minute records
        """
        columns = """
            id, camera_id, timestamp, video_path, height, width, downscale_factor,
            frame_count, total_intensity, max_intensity, nonzero_pixels, processed_at
        """
        if include_arrays:
            columns = f"intensity_array, {columns}"

        try:
            with self.get_cursor() as cur:
                cur.execute(f"""
                    SELECT {columns}
                    FROM heatmap_minutes
                    WHERE camera_id = %s
                      AND timestamp >= %s
                      AND timestamp < %s
                    ORDER BY timestamp
                """, (camera_id, start_time, end_time))

                results = cur.fetchall()
                logger.info(f"Retrieved {len(results)} heatmap minutes")
                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Failed to retrieve heatmap minutes: {e}")
            return []

    def get_activity_stats(self, camera_id: str, start_time: datetime, end_time: datetime,
                           interval: str = 'hour') -> List[dict]:
        """
        Get aggregated activity statistics for a time range.

        Args:
            camera_id: Camera identifier
            start_time: Start of time range
            end_time: End of time range
            interval: Aggregation interval ('hour', 'day', 'week')

        Returns:
            List of aggregated statistics
        """
        valid_intervals = ['hour', 'day', 'week']
        if interval not in valid_intervals:
            interval = 'hour'

        try:
            with self.get_cursor() as cur:
                cur.execute(f"""
                    SELECT 
                        DATE_TRUNC(%s, timestamp) as period,
                        COUNT(*) as minute_count,
                        SUM(total_intensity) as total_activity,
                        AVG(total_intensity) as avg_activity,
                        MAX(max_intensity) as peak_intensity,
                        SUM(frame_count) as total_frames,
                        MIN(timestamp) as period_start,
                        MAX(timestamp) as period_end
                    FROM heatmap_minutes
                    WHERE camera_id = %s
                      AND timestamp >= %s
                      AND timestamp < %s
                    GROUP BY period
                    ORDER BY period
                """, (interval, camera_id, start_time, end_time))

                results = cur.fetchall()
                logger.info(f"Retrieved {len(results)} activity stat periods")
                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Failed to retrieve activity stats: {e}")
            return []

    def get_latest_timestamp(self, camera_id: str) -> Optional[datetime]:
        """
        Get the timestamp of the most recent heatmap data for a camera.

        Args:
            camera_id: Camera identifier

        Returns:
            Latest timestamp, or None if no data exists
        """
        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT MAX(timestamp) as latest
                    FROM heatmap_minutes
                    WHERE camera_id = %s
                """, (camera_id,))

                result = cur.fetchone()
                return result['latest'] if result and result['latest'] else None

        except Exception as e:
            logger.error(f"Failed to get latest timestamp: {e}")
            return None

    def check_minute_exists(self, camera_id: str, timestamp: datetime) -> bool:
        """
        Check if a heatmap minute already exists.

        Args:
            camera_id: Camera identifier
            timestamp: Minute timestamp to check

        Returns:
            True if exists, False otherwise
        """
        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT 1
                    FROM heatmap_minutes
                    WHERE camera_id = %s AND timestamp = %s
                """, (camera_id, timestamp))

                return cur.fetchone() is not None

        except Exception as e:
            logger.error(f"Failed to check minute existence: {e}")
            return False

    def delete_old_data(self, retention_days: int = 90) -> int:
        """
        Delete heatmap data older than retention period.

        Args:
            retention_days: Number of days to keep

        Returns:
            Number of rows deleted
        """
        try:
            with self.get_cursor() as cur:
                cutoff_date = datetime.now() - timedelta(days=retention_days)

                cur.execute("""
                    DELETE FROM heatmap_minutes
                    WHERE timestamp < %s
                """, (cutoff_date,))

                deleted = cur.rowcount
                logger.info(
                    f"Deleted {deleted} old heatmap records (older than {retention_days} days)")
                return deleted

        except Exception as e:
            logger.error(f"Failed to delete old data: {e}")
            return 0

    def get_database_stats(self) -> dict:
        """
        Get database statistics.

        Returns:
            Dictionary with database stats
        """
        try:
            with self.get_cursor() as cur:
                # Get table size
                cur.execute("""
                    SELECT pg_size_pretty(pg_total_relation_size('heatmap_minutes')) as total_size
                """)
                size_result = cur.fetchone()

                # Get row count and date range
                cur.execute("""
                    SELECT 
                        COUNT(*) as row_count,
                        MIN(timestamp) as earliest_data,
                        MAX(timestamp) as latest_data,
                        COUNT(DISTINCT camera_id) as camera_count
                    FROM heatmap_minutes
                """)
                stats_result = cur.fetchone()

                return {
                    'total_size': size_result['total_size'] if size_result else 'Unknown',
                    'row_count': stats_result['row_count'] if stats_result else 0,
                    'earliest_data': stats_result['earliest_data'] if stats_result else None,
                    'latest_data': stats_result['latest_data'] if stats_result else None,
                    'camera_count': stats_result['camera_count'] if stats_result else 0,
                }

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    def close(self):
        """Close all database connections."""
        if hasattr(self, 'pool'):
            self.pool.closeall()
            logger.info("Database connection pool closed")
