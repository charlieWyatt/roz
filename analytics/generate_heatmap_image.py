"""
Generate static heatmap images from PostgreSQL data.

Usage:
    # Last hour
    python generate_heatmap_image.py --hours 1 --output heatmap_last_hour.jpg
    
    # Specific date
    python generate_heatmap_image.py --date "2025-10-20" --output heatmap_oct20.jpg
    
    # Specific time range
    python generate_heatmap_image.py --start "2025-10-20 14:00:00" --end "2025-10-20 15:00:00" --output heatmap_2pm.jpg
    
    # With background frame
    python generate_heatmap_image.py --hours 1 --output heatmap.jpg --with-background --video-path raw_videos/2025/10/20/clip.mp4
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import sys

from db_client import DatabaseClient
from db_helpers import S3Manager
from heatmap_writer import HeatmapWriter, HeatmapVisualizer
from heatmap_helpers import get_reference_frame
import config


def parse_datetime(date_string: str) -> datetime:
    """Parse various datetime formats."""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue

    raise ValueError(f"Could not parse datetime: {date_string}")


def download_video_for_background(s3_manager: S3Manager, video_path: str) -> Path:
    """Download a video to get a reference frame."""
    local_path = Path(config.LOCAL_DOWNLOADS_DIR) / Path(video_path).name

    if not local_path.exists():
        print(f"Downloading video for background frame: {video_path}")
        s3_manager.download_file(video_path, str(local_path))

    return local_path


def main():
    parser = argparse.ArgumentParser(
        description='Generate heatmap images from PostgreSQL data'
    )

    # Time range options (mutually exclusive groups)
    time_group = parser.add_mutually_exclusive_group(required=True)
    time_group.add_argument(
        '--hours',
        type=float,
        help='Generate heatmap for last N hours'
    )
    time_group.add_argument(
        '--date',
        type=str,
        help='Generate heatmap for specific date (YYYY-MM-DD)'
    )
    time_group.add_argument(
        '--start',
        type=str,
        help='Start datetime (YYYY-MM-DD HH:MM:SS)'
    )

    # Additional options
    parser.add_argument(
        '--end',
        type=str,
        help='End datetime (required with --start)'
    )
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output image path (e.g., heatmap.jpg)'
    )
    parser.add_argument(
        '--camera-id',
        type=str,
        default='default',
        help='Camera ID (default: default)'
    )
    parser.add_argument(
        '--operation',
        type=str,
        choices=['sum', 'mean'],
        default='sum',
        help='Aggregation operation (default: sum)'
    )
    parser.add_argument(
        '--with-background',
        action='store_true',
        help='Overlay on video background frame'
    )
    parser.add_argument(
        '--video-path',
        type=str,
        help='S3 video path for background (required with --with-background)'
    )
    parser.add_argument(
        '--colormap',
        type=str,
        default='jet',
        help='Matplotlib colormap (default: jet)'
    )
    parser.add_argument(
        '--alpha',
        type=float,
        default=0.6,
        help='Transparency (0-1, default: 0.6)'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.start and not args.end:
        parser.error("--end is required when using --start")

    if args.with_background and not args.video_path:
        parser.error("--video-path is required when using --with-background")

    # Calculate time range
    now = datetime.now()

    if args.hours:
        end_time = now
        start_time = now - timedelta(hours=args.hours)
        print(f"Time range: Last {args.hours} hour(s)")
    elif args.date:
        date = parse_datetime(args.date)
        start_time = date.replace(hour=0, minute=0, second=0)
        end_time = start_time + timedelta(days=1)
        print(f"Time range: {args.date} (full day)")
    else:  # args.start
        start_time = parse_datetime(args.start)
        end_time = parse_datetime(args.end)
        print(f"Time range: {start_time} to {end_time}")

    print(f"Start: {start_time}")
    print(f"End:   {end_time}")
    print(f"Duration: {end_time - start_time}")
    print()

    # Connect to database
    print("Connecting to database...")
    db = DatabaseClient(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD
    )

    writer = HeatmapWriter(db, camera_id=args.camera_id)

    # Get aggregated heatmap from database
    print(f"Querying database for camera '{args.camera_id}'...")
    heatmap = writer.aggregate_heatmaps(
        start_time, end_time, operation=args.operation)

    if heatmap is None:
        print("❌ No data found for specified time range!")
        print("\nTip: Check what data exists:")
        print(
            f"  psql postgresql://charlie:Sj28Qb50@localhost:5432/roz -c \"SELECT MIN(timestamp), MAX(timestamp) FROM heatmap_minutes WHERE camera_id='{args.camera_id}';\"")
        sys.exit(1)

    print(f"✓ Retrieved data (aggregated using {args.operation})")
    print(f"  Shape: {heatmap.shape}")
    print(f"  Total intensity: {heatmap.sum():.1f}")
    print(f"  Peak intensity: {heatmap.max():.1f}")
    print()

    # Get reference frame if requested
    reference_frame = None
    if args.with_background:
        print("Getting background frame...")

        # Initialize S3 manager
        s3_manager = S3Manager(
            endpoint_url=config.S3_ENDPOINT_URL,
            access_key=config.S3_ACCESS_KEY,
            secret_key=config.S3_SECRET_KEY,
            bucket_name=config.S3_BUCKET_NAME,
            videos_prefix=config.S3_VIDEOS_PREFIX,
            heatmaps_prefix=config.S3_HEATMAPS_PREFIX
        )

        # Download video if needed
        video_path = download_video_for_background(s3_manager, args.video_path)

        # Get middle frame
        reference_frame = get_reference_frame(video_path)

        if reference_frame is not None:
            print(f"✓ Got reference frame from {args.video_path}")
        else:
            print(f"⚠️  Could not get reference frame, using plain heatmap")

    # Generate image
    print(f"Generating image: {args.output}")
    config.ensure_directories()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    HeatmapVisualizer.save_heatmap_image(
        heatmap,
        str(output_path),
        reference_frame=reference_frame,
        colormap=args.colormap,
        alpha=args.alpha
    )

    print(f"✓ Saved: {output_path}")
    print(f"  Size: {output_path.stat().st_size / 1024:.1f} KB")

    # Cleanup
    db.close()

    print("\n✓ Done!")


if __name__ == '__main__':
    main()
