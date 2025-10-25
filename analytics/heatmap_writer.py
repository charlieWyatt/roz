"""
Handles writing heatmap data to the database.
Includes serialization/deserialization of numpy arrays.
"""

import numpy as np
import zlib
from typing import List, Optional
import logging
from datetime import datetime

from db_client import DatabaseClient
from heatmap_processor import HeatmapMinute

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HeatmapWriter:
    """Writes heatmap data to PostgreSQL database."""

    def __init__(self, db_client: DatabaseClient, camera_id: str = 'default'):
        """
        Initialize heatmap writer.

        Args:
            db_client: Database client instance
            camera_id: Camera identifier
        """
        self.db = db_client
        self.camera_id = camera_id

    @staticmethod
    def serialize_heatmap(heatmap: np.ndarray) -> bytes:
        """
        Convert numpy array to compressed bytes for database storage.

        Args:
            heatmap: 2D numpy array of float32 values

        Returns:
            Compressed bytes
        """
        # Ensure float32 dtype
        if heatmap.dtype != np.float32:
            heatmap = heatmap.astype(np.float32)

        # Convert to bytes and compress
        raw_bytes = heatmap.tobytes()
        # Good balance of speed/compression
        compressed = zlib.compress(raw_bytes, level=6)

        # Log compression ratio
        ratio = (1 - len(compressed) / len(raw_bytes)) * 100
        logger.debug(
            f"Compressed {len(raw_bytes)} bytes -> {len(compressed)} bytes ({ratio:.1f}% reduction)")

        return compressed

    @staticmethod
    def deserialize_heatmap(data: bytes, height: int, width: int) -> np.ndarray:
        """
        Reconstruct numpy array from database bytes.

        Args:
            data: Compressed bytes from database
            height: Array height
            width: Array width

        Returns:
            2D numpy array of float32 values
        """
        # Decompress
        decompressed = zlib.decompress(data)

        # Convert back to numpy array
        heatmap = np.frombuffer(decompressed, dtype=np.float32)
        return heatmap.reshape(height, width)

    def write_minute(self, minute: HeatmapMinute, video_path: str, downscale_factor: float) -> bool:
        """
        Write a single minute of heatmap data to the database.

        Args:
            minute: HeatmapMinute object containing the data
            video_path: S3 key of source video
            downscale_factor: Downscale factor used

        Returns:
            True if successful, False otherwise
        """
        try:
            # Serialize the heatmap array
            intensity_array = self.serialize_heatmap(minute.heatmap)

            # Get dimensions
            height, width = minute.heatmap.shape

            # Insert into database
            row_id = self.db.insert_heatmap_minute(
                camera_id=self.camera_id,
                timestamp=minute.timestamp,
                video_path=video_path,
                height=height,
                width=width,
                downscale_factor=downscale_factor,
                intensity_array=intensity_array,
                frame_count=minute.frame_count,
                total_intensity=minute.total_intensity,
                max_intensity=minute.max_intensity,
                nonzero_pixels=minute.nonzero_pixels
            )

            if row_id:
                logger.debug(f"Wrote minute {minute.timestamp} (id={row_id})")
                return True
            else:
                logger.error(f"Failed to write minute {minute.timestamp}")
                return False

        except Exception as e:
            logger.error(f"Error writing minute {minute.timestamp}: {e}")
            return False

    def write_minutes_batch(self, minutes: List[HeatmapMinute], video_path: str,
                            downscale_factor: float) -> int:
        """
        Write multiple minutes in batch.

        Args:
            minutes: List of HeatmapMinute objects
            video_path: S3 key of source video
            downscale_factor: Downscale factor used

        Returns:
            Number of successfully written minutes
        """
        success_count = 0

        logger.info(f"Writing {len(minutes)} minutes to database...")

        for minute in minutes:
            if self.write_minute(minute, video_path, downscale_factor):
                success_count += 1

        logger.info(
            f"Successfully wrote {success_count}/{len(minutes)} minutes")

        return success_count

    def aggregate_heatmaps(self, start_time: datetime, end_time: datetime,
                           operation: str = 'sum') -> Optional[np.ndarray]:
        """
        Aggregate heatmaps over a time range.

        Args:
            start_time: Start of time range
            end_time: End of time range
            operation: 'sum' or 'mean'

        Returns:
            Aggregated heatmap array or None if no data
        """
        try:
            # Get all minutes in range
            results = self.db.get_heatmap_minutes(
                camera_id=self.camera_id,
                start_time=start_time,
                end_time=end_time,
                include_arrays=True
            )

            if not results:
                logger.warning(
                    f"No data found for range {start_time} - {end_time}")
                return None

            logger.info(f"Aggregating {len(results)} minutes ({operation})...")

            # Deserialize and aggregate
            arrays = []
            for result in results:
                heatmap = self.deserialize_heatmap(
                    result['intensity_array'],
                    result['height'],
                    result['width']
                )
                arrays.append(heatmap)

            # Perform aggregation
            if operation == 'sum':
                aggregated = np.sum(arrays, axis=0)
            elif operation == 'mean':
                aggregated = np.mean(arrays, axis=0)
            else:
                raise ValueError(f"Unknown operation: {operation}")

            logger.info(f"Aggregated {len(arrays)} arrays using {operation}")
            return aggregated

        except Exception as e:
            logger.error(f"Error aggregating heatmaps: {e}")
            return None

    def check_video_processed(self, video_path: str) -> tuple[bool, int]:
        """Check if video processed and return (processed, minute_count)."""
        try:
            with self.db.get_cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) as count FROM heatmap_minutes WHERE video_path = %s",
                    (video_path,)
                )
                count = cur.fetchone()['count']
                return count > 0, count
        except Exception as e:
            logger.error(f"Error checking video: {e}")
            return False, 0


class HeatmapVisualizer:
    """Helper class to create visualizations from database heatmaps."""

    @staticmethod
    def save_heatmap_image(heatmap: np.ndarray, output_path: str,
                           reference_frame: Optional[np.ndarray] = None,
                           colormap: str = 'jet', alpha: float = 0.6):
        """
        Save heatmap as image file (same as before, but takes numpy array).

        Args:
            heatmap: Heatmap array (can be aggregated from multiple minutes)
            output_path: Path to save image
            reference_frame: Optional background frame
            colormap: Matplotlib colormap name
            alpha: Transparency (0-1)
        """
        import cv2
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')

        # Normalize
        if heatmap.max() > 0:
            normalized = heatmap / heatmap.max()
        else:
            normalized = heatmap

        # Apply gaussian blur
        blurred = cv2.GaussianBlur(normalized, (51, 51), 0)

        # Create figure
        fig, ax = plt.subplots(figsize=(16, 9), dpi=150)

        # Background frame if provided
        if reference_frame is not None:
            ax.imshow(cv2.cvtColor(reference_frame, cv2.COLOR_BGR2RGB))

        # Overlay heatmap
        ax.imshow(blurred, cmap=colormap, alpha=alpha,
                  interpolation='bilinear')
        ax.axis('off')

        # Save
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches='tight', dpi=150, format='jpg')
        plt.close(fig)

        logger.info(f"Saved heatmap visualization to {output_path}")
