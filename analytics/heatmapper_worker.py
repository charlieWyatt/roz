"""
Heatmapper Worker - Generates and stores heatmap data from S3 videos.

New database-backed workflow:
1. Downloads videos from S3
2. Processes videos minute-by-minute
3. Stores raw heatmap data in PostgreSQL
4. Can optionally generate image files for preview

Can be run on a cron job to continuously process new videos.
"""

import os
import argparse
from pathlib import Path
from typing import Optional
import logging

from db_helpers import S3Manager
from db_client import DatabaseClient
from heatmap_processor import VideoHeatmapProcessor
from heatmap_writer import HeatmapWriter, HeatmapVisualizer
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_video(s3_manager: S3Manager, video_key: str) -> Path:
    """Download video from S3 to local storage."""
    local_path = Path(config.LOCAL_DOWNLOADS_DIR) / Path(video_key).name
    s3_manager.download_file(video_key, str(local_path))
    return local_path


def cleanup_files(*paths: Path):
    """Delete local files."""
    for path in paths:
        if path.exists():
            os.remove(path)
            logger.debug(f"Cleaned up: {path}")


def process_video_to_database(s3_manager: S3Manager, db_client: DatabaseClient,
                              video_key: str, generate_preview: bool = False) -> bool:
    """Process video: download → analyze → store in database."""
    try:
        processor = VideoHeatmapProcessor(downscale=config.DOWNSCALE)
        writer = HeatmapWriter(db_client, camera_id=config.CAMERA_ID)

        # Check if already processed
        processed, minute_count = writer.check_video_processed(video_key)
        if processed:
            logger.info(
                f"✓ Skipped (already processed): {video_key} ({minute_count} min)")
            return True

        # Download and parse timestamp
        video_path = download_video(s3_manager, video_key)
        start_time = processor.parse_timestamp_from_filename(
            Path(video_key).name)

        if not start_time:
            logger.warning(f"✗ Invalid filename format: {video_key}")
            cleanup_files(video_path) if config.CLEANUP_LOCAL_FILES else None
            return False

        # Process video
        logger.info(f"Processing: {video_key} (started {start_time})")
        minutes = processor.process_video(video_path, start_time)

        if not minutes:
            logger.error("✗ No data generated")
            cleanup_files(video_path) if config.CLEANUP_LOCAL_FILES else None
            return False

        # Write to database
        success_count = writer.write_minutes_batch(
            minutes, video_key, config.DOWNSCALE)

        # Optional preview
        if generate_preview and minutes:
            try:
                import numpy as np
                aggregated = np.sum([m.heatmap for m in minutes], axis=0)
                reference_frame = None

                if config.USE_BACKGROUND:
                    from heatmap_helpers import get_reference_frame
                    reference_frame = get_reference_frame(video_path)

                preview_path = Path(config.LOCAL_HEATMAPS_DIR) / \
                    f"{video_path.stem}_preview.jpg"
                HeatmapVisualizer.save_heatmap_image(
                    aggregated, str(preview_path), reference_frame)
            except Exception as e:
                logger.warning(f"Preview failed: {e}")

        cleanup_files(video_path) if config.CLEANUP_LOCAL_FILES else None
        logger.info(
            f"✓ Completed: {success_count}/{len(minutes)} minutes written")
        return success_count > 0

    except Exception as e:
        logger.error(f"✗ Failed: {video_key} - {e}")
        return False


def run_worker(date_prefix: str = "", max_videos: Optional[int] = None,
               generate_previews: bool = False):
    """Main worker: scans S3, processes videos, stores in database."""
    config.ensure_directories()

    # Initialize connections
    s3_manager = S3Manager(
        endpoint_url=config.S3_ENDPOINT_URL,
        access_key=config.S3_ACCESS_KEY,
        secret_key=config.S3_SECRET_KEY,
        bucket_name=config.S3_BUCKET_NAME,
        videos_prefix=config.S3_VIDEOS_PREFIX,
        heatmaps_prefix=config.S3_HEATMAPS_PREFIX
    )

    try:
        # Try connection string first (better for Supabase IPv4 compatibility)
        if config.DB_CONNECTION_STRING:
            logger.info("Using connection string for database")
            db_client = DatabaseClient(
                connection_string=config.DB_CONNECTION_STRING)
        else:
            logger.info("Using individual DB parameters")
            db_client = DatabaseClient(
                host=config.DB_HOST, port=config.DB_PORT, dbname=config.DB_NAME,
                user=config.DB_USER, password=config.DB_PASSWORD
            )

        if not db_client.test_connection():
            logger.error("Database connection failed")
            return
    except Exception as e:
        logger.error(f"Database error: {e}")
        return

    # Get videos
    videos = s3_manager.list_videos(date_prefix)
    if not videos:
        logger.info("No videos found")
        db_client.close()
        return

    if max_videos and len(videos) > max_videos:
        videos = videos[:max_videos]

    logger.info(f"Processing {len(videos)} videos...")

    # Process each video
    successful = 0
    for i, video_key in enumerate(videos, 1):
        logger.info(f"[{i}/{len(videos)}] {video_key}")
        if process_video_to_database(s3_manager, db_client, video_key, generate_previews):
            successful += 1

    # Summary
    stats = db_client.get_database_stats()
    logger.info(f"\n✓ Complete: {successful}/{len(videos)} successful")
    logger.info(
        f"Database: {stats.get('row_count', 0)} records, {stats.get('total_size', 'unknown')}")
    db_client.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate and store heatmaps from S3 videos (database mode)'
    )
    parser.add_argument(
        '--date-prefix',
        type=str,
        default='',
        help='Date prefix filter (e.g., 2025/10/20/)'
    )
    parser.add_argument(
        '--max-videos',
        type=int,
        default=None,
        help='Max videos to process'
    )
    parser.add_argument(
        '--generate-previews',
        action='store_true',
        help='Generate preview images (slower)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics and exit'
    )

    args = parser.parse_args()

    # If stats mode, just show stats and exit
    if args.stats:
        try:
            # Use connection string for Supabase IPv4 compatibility
            if config.DB_CONNECTION_STRING:
                logger.info("Using connection string for database")
                db_client = DatabaseClient(
                    connection_string=config.DB_CONNECTION_STRING)
            else:
                logger.info("Using individual DB parameters")
                db_client = DatabaseClient(
                    host=config.DB_HOST,
                    port=config.DB_PORT,
                    dbname=config.DB_NAME,
                    user=config.DB_USER,
                    password=config.DB_PASSWORD
                )

            stats = db_client.get_database_stats()
            print("\n" + "=" * 60)
            print("DATABASE STATISTICS")
            print("=" * 60)
            print(f"Total records: {stats.get('row_count', 0):,}")
            print(f"Database size: {stats.get('total_size', 'unknown')}")
            print(f"Cameras: {stats.get('camera_count', 0)}")
            print(f"Earliest data: {stats.get('earliest_data', 'N/A')}")
            print(f"Latest data: {stats.get('latest_data', 'N/A')}")
            print("=" * 60)

            db_client.close()

        except Exception as e:
            print(f"Error connecting to database: {e}")

        return

    # Run worker
    max_videos = args.max_videos or config.MAX_VIDEOS_PER_RUN
    date_prefix = args.date_prefix or config.VIDEO_PREFIX

    run_worker(
        date_prefix=date_prefix,
        max_videos=max_videos,
        generate_previews=args.generate_previews
    )


if __name__ == '__main__':
    main()
