"""
S3 bucket structure migration script.

Migrates from flat structure:
  2025/10/20/14/clip.mp4
  
To hierarchical structure:
  raw_videos/2025/10/20/14/clip.mp4
  heatmaps/2025/10/20/14/heatmap.jpg
"""

import argparse
import sys
from db_helpers import S3Manager
import config


def migrate_videos(s3_manager, dry_run=True):
    """
    Move all videos from flat structure to raw_videos/ prefix.

    Args:
        s3_manager: S3Manager instance
        dry_run: If True, only print what would be done
    """
    print("=" * 60)
    print("S3 VIDEO MIGRATION: Flat → raw_videos/")
    print("=" * 60)
    print()

    # List all objects that look like videos (start with year pattern)
    print("Scanning for videos in bucket...")

    response = s3_manager.s3_client.list_objects_v2(
        Bucket=s3_manager.bucket_name,
        Prefix='2025/'  # Assuming videos start with year
    )

    if 'Contents' not in response:
        print("No videos found to migrate.")
        return 0

    videos_to_migrate = []

    for obj in response['Contents']:
        key = obj['Key']

        # Skip if already in raw_videos/ or heatmaps/
        if key.startswith('raw_videos/') or key.startswith('heatmaps/'):
            continue

        # Only migrate .mp4 files
        if key.endswith('.mp4'):
            videos_to_migrate.append(key)

    print(f"Found {len(videos_to_migrate)} videos to migrate")
    print()

    if not videos_to_migrate:
        print("✓ No migration needed - all videos already in correct location")
        return 0

    # Show first few examples
    print("Examples:")
    for video in videos_to_migrate[:5]:
        new_key = f"raw_videos/{video}"
        print(f"  {video}")
        print(f"  → {new_key}")
        print()

    if len(videos_to_migrate) > 5:
        print(f"  ... and {len(videos_to_migrate) - 5} more")
        print()

    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE - No changes made")
        print("=" * 60)
        print()
        print("To actually perform the migration, run with --execute flag:")
        print("  python analytics/migrate_s3_structure.py --execute")
        return len(videos_to_migrate)

    # Actual migration
    print("=" * 60)
    print("STARTING MIGRATION")
    print("=" * 60)
    print()

    migrated = 0
    failed = 0

    for i, old_key in enumerate(videos_to_migrate, 1):
        new_key = f"raw_videos/{old_key}"

        try:
            # Copy to new location
            print(f"[{i}/{len(videos_to_migrate)}] Copying {old_key}...")
            s3_manager.s3_client.copy_object(
                Bucket=s3_manager.bucket_name,
                CopySource={'Bucket': s3_manager.bucket_name, 'Key': old_key},
                Key=new_key
            )

            # Delete old location
            s3_manager.s3_client.delete_object(
                Bucket=s3_manager.bucket_name,
                Key=old_key
            )

            migrated += 1
            print(f"  ✓ Migrated to {new_key}")

        except Exception as e:
            failed += 1
            print(f"  ✗ Error: {e}")

    print()
    print("=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"Migrated: {migrated}")
    print(f"Failed:   {failed}")
    print()

    return migrated


def migrate_heatmaps(s3_manager, dry_run=True):
    """
    Move all heatmaps from flat structure to heatmaps/ prefix.

    Args:
        s3_manager: S3Manager instance
        dry_run: If True, only print what would be done
    """
    print("=" * 60)
    print("S3 HEATMAP MIGRATION: Flat → heatmaps/")
    print("=" * 60)
    print()

    # List all objects that look like heatmaps
    print("Scanning for heatmaps in bucket...")

    response = s3_manager.s3_client.list_objects_v2(
        Bucket=s3_manager.bucket_name,
        Prefix='2025/'
    )

    if 'Contents' not in response:
        print("No heatmaps found to migrate.")
        return 0

    heatmaps_to_migrate = []

    for obj in response['Contents']:
        key = obj['Key']

        # Skip if already in raw_videos/ or heatmaps/
        if key.startswith('raw_videos/') or key.startswith('heatmaps/'):
            continue

        # Only migrate .jpg files (heatmaps)
        if key.endswith('.jpg') or key.endswith('.jpeg') or key.endswith('.png'):
            heatmaps_to_migrate.append(key)

    print(f"Found {len(heatmaps_to_migrate)} heatmaps to migrate")
    print()

    if not heatmaps_to_migrate:
        print("✓ No migration needed - all heatmaps already in correct location")
        return 0

    # Show first few examples
    print("Examples:")
    for heatmap in heatmaps_to_migrate[:5]:
        new_key = f"heatmaps/{heatmap}"
        print(f"  {heatmap}")
        print(f"  → {new_key}")
        print()

    if len(heatmaps_to_migrate) > 5:
        print(f"  ... and {len(heatmaps_to_migrate) - 5} more")
        print()

    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE - No changes made")
        print("=" * 60)
        return len(heatmaps_to_migrate)

    # Actual migration
    print("=" * 60)
    print("STARTING MIGRATION")
    print("=" * 60)
    print()

    migrated = 0
    failed = 0

    for i, old_key in enumerate(heatmaps_to_migrate, 1):
        new_key = f"heatmaps/{old_key}"

        try:
            # Copy to new location
            print(f"[{i}/{len(heatmaps_to_migrate)}] Copying {old_key}...")
            s3_manager.s3_client.copy_object(
                Bucket=s3_manager.bucket_name,
                CopySource={'Bucket': s3_manager.bucket_name, 'Key': old_key},
                Key=new_key
            )

            # Delete old location
            s3_manager.s3_client.delete_object(
                Bucket=s3_manager.bucket_name,
                Key=old_key
            )

            migrated += 1
            print(f"  ✓ Migrated to {new_key}")

        except Exception as e:
            failed += 1
            print(f"  ✗ Error: {e}")

    print()
    print("=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"Migrated: {migrated}")
    print(f"Failed:   {failed}")
    print()

    return migrated


def main():
    parser = argparse.ArgumentParser(
        description='Migrate S3 bucket structure to use raw_videos/ and heatmaps/ prefixes'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually perform the migration (default is dry-run)'
    )
    parser.add_argument(
        '--videos-only',
        action='store_true',
        help='Only migrate videos'
    )
    parser.add_argument(
        '--heatmaps-only',
        action='store_true',
        help='Only migrate heatmaps'
    )

    args = parser.parse_args()

    dry_run = not args.execute

    print()
    print("S3 BUCKET STRUCTURE MIGRATION")
    print("=" * 60)
    print(f"Bucket:  {config.S3_BUCKET_NAME}")
    print(f"Mode:    {'EXECUTE' if args.execute else 'DRY RUN'}")
    print("=" * 60)
    print()

    if dry_run:
        print("⚠️  DRY RUN MODE - No actual changes will be made")
        print()

    # Initialize S3 manager
    s3_manager = S3Manager(
        endpoint_url=config.S3_ENDPOINT_URL,
        access_key=config.S3_ACCESS_KEY,
        secret_key=config.S3_SECRET_KEY,
        bucket_name=config.S3_BUCKET_NAME,
        videos_prefix='',  # Empty for now - we're migrating
        heatmaps_prefix=''
    )

    total_migrated = 0

    # Migrate videos
    if not args.heatmaps_only:
        video_count = migrate_videos(s3_manager, dry_run)
        total_migrated += video_count if not dry_run else 0

    # Migrate heatmaps
    if not args.videos_only:
        heatmap_count = migrate_heatmaps(s3_manager, dry_run)
        total_migrated += heatmap_count if not dry_run else 0

    if dry_run:
        print()
        print("To execute this migration, run:")
        print("  python analytics/migrate_s3_structure.py --execute")
    else:
        print()
        print(f"✓ Migration complete! Migrated {total_migrated} files total")


if __name__ == '__main__':
    main()
