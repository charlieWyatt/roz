"""
Heatmapper Worker - Generates foot traffic heatmaps from S3 videos.
Can be run on a cron job to process videos without heatmaps.
"""

import os
import argparse
from pathlib import Path
from typing import Optional

from db_helpers import S3Manager
from heatmap_helpers import create_heatmap_from_video
import config


def download_video(s3_manager: S3Manager, video_key: str) -> Path:
    """Download video from S3 to local storage."""
    local_path = Path(config.LOCAL_DOWNLOADS_DIR) / Path(video_key).name
    s3_manager.download_file(video_key, str(local_path))
    return local_path


def generate_heatmap(video_path: Path) -> Path:
    """Generate heatmap from video."""
    output_path = Path(config.LOCAL_HEATMAPS_DIR) / \
        f"{video_path.stem}_heatmap.jpg"
    create_heatmap_from_video(video_path, output_path,
                              use_background=config.USE_BACKGROUND)
    return output_path


def upload_heatmap(s3_manager: S3Manager, local_path: Path, video_key: str):
    """Upload heatmap to S3."""
    heatmap_key = s3_manager.get_heatmap_key_for_video(
        video_key, extension='.jpg')
    s3_manager.upload_file(str(local_path), heatmap_key,
                           content_type='image/jpeg')


def cleanup_files(*paths: Path):
    """Delete local files."""
    for path in paths:
        if path.exists():
            os.remove(path)


def process_video(s3_manager: S3Manager, video_key: str) -> bool:
    """
    Process a single video: download → generate heatmap → upload.

    Returns True if successful, False otherwise.
    """
    try:
        print(f"Processing: {video_key}")

        # Download
        video_path = download_video(s3_manager, video_key)

        # Generate heatmap
        heatmap_path = generate_heatmap(video_path)

        # Upload
        upload_heatmap(s3_manager, heatmap_path, video_key)

        # Cleanup
        if config.CLEANUP_LOCAL_FILES:
            cleanup_files(video_path, heatmap_path)

        print(f"✓ {video_key}")
        return True

    except Exception as e:
        print(f"✗ Failed: {video_key} - {e}")
        return False


def run_worker(prefix: str = "", max_videos: Optional[int] = None):
    """
    Main worker function.

    Args:
        prefix: S3 prefix to filter videos (e.g., '2025/10/20/')
        max_videos: Maximum number of videos to process
    """
    # Ensure directories exist
    config.ensure_directories()

    # Initialize S3 manager
    s3_manager = S3Manager(
        endpoint_url=config.S3_ENDPOINT_URL,
        access_key=config.S3_ACCESS_KEY,
        secret_key=config.S3_SECRET_KEY,
        bucket_name=config.S3_BUCKET_NAME
    )

    # Get videos to process
    videos = s3_manager.get_videos_without_heatmaps(prefix)

    if not videos:
        print("No videos to process.")
        return

    # Limit if specified
    if max_videos and len(videos) > max_videos:
        videos = videos[:max_videos]

    # Process videos
    print(f"\nProcessing {len(videos)} videos...\n")

    successful = 0
    for video_key in videos:
        if process_video(s3_manager, video_key):
            successful += 1

    print(f"\nComplete: {successful}/{len(videos)} successful")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate heatmaps from S3 videos')
    parser.add_argument('--prefix', type=str, default='',
                        help='S3 prefix filter')
    parser.add_argument('--max-videos', type=int,
                        default=None, help='Max videos to process')

    args = parser.parse_args()

    max_videos = args.max_videos or config.MAX_VIDEOS_PER_RUN
    prefix = args.prefix or config.VIDEO_PREFIX

    run_worker(prefix=prefix, max_videos=max_videos)


if __name__ == '__main__':
    main()
