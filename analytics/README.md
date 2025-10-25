# Foot Traffic Heatmap Generator

Automatically generates foot traffic heatmaps from surveillance videos stored in S3/Cloudflare R2.

## How It Works

Uses background subtraction to detect motion and creates a heatmap showing where the most activity occurs in your videos.

## Quick Start

### 1. Install

```bash
cd analytics
poetry install
poetry shell
```

Or with pip:

```bash
cd analytics
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

Copy `.env.example` to `.env` and add your S3 credentials:

```bash
cp .env.example .env
# Edit .env with your S3_ACCESS_KEY and S3_SECRET_KEY
```

### 3. Run

Process all videos without heatmaps:

```bash
python heatmapper_worker.py
```

Process specific date:

```bash
python heatmapper_worker.py --date-prefix "2025/10/20/"
```

Limit number of videos:

```bash
python heatmapper_worker.py --max-videos 5
```

## File Structure

```
analytics/
├── db_helpers.py              # S3 operations
├── heatmap_helpers.py         # Heatmap generation
├── heatmapper_worker.py       # Main worker script
├── migrate_s3_structure.py    # Migration script
├── config.py                  # Configuration
├── requirements.txt           # Dependencies
├── README.md                  # This file
└── MIGRATION_README.md        # Migration guide
```

## Configuration

Edit `.env` file:

- **S3_ACCESS_KEY** / **S3_SECRET_KEY**: Your S3 credentials (required)
- **S3_VIDEOS_PREFIX**: Videos directory in S3 (default: "raw_videos/")
- **S3_HEATMAPS_PREFIX**: Heatmaps directory in S3 (default: "heatmaps/")
- **VIDEO_PREFIX**: Filter videos by date path (e.g., "2025/10/20/")
- **MAX_VIDEOS_PER_RUN**: Limit videos per run (default: 10)
- **USE_BACKGROUND**: Overlay on video frame (default: true)
- **DOWNSCALE**: Processing scale (default: 0.25, lower = faster)
- **CLEANUP_LOCAL_FILES**: Delete temp files (default: true)

## Cron Job

Run every hour:

```bash
crontab -e
```

Add:

```
0 * * * * cd /path/to/analytics && ./venv/bin/python heatmapper_worker.py >> cron.log 2>&1
```

## S3 Bucket Structure

Videos are stored in `raw_videos/`:

```
raw_videos/
└── 2025/
    └── 10/
        └── 20/
            └── 13/
                └── clip_2025-10-20_13-57-04.mp4
```

Heatmaps (auto-generated) are stored in `heatmaps/`:

```
heatmaps/
└── 2025/
    └── 10/
        └── 20/
            └── 13/
                └── clip_2025-10-20_13-57-04_heatmap.jpg
```

### Migrating from Old Structure

If you have an existing bucket with the old flat structure, see [MIGRATION_README.md](./MIGRATION_README.md) for migration instructions.

## Dependencies

- **boto3**: S3 operations
- **opencv-python**: Video processing
- **numpy**: Array operations
- **matplotlib**: Heatmap visualization
- **python-dotenv**: Environment variable loading

## Scripts

### heatmapper_worker.py

Main worker that processes videos and generates heatmaps.

```bash
python heatmapper_worker.py [--date-prefix DATE] [--max-videos N]
```

### migrate_s3_structure.py

Migrates existing S3 bucket from old flat structure to new organized structure.

```bash
python migrate_s3_structure.py [--apply] [--cleanup] [--verbose]
```

See [MIGRATION_README.md](./MIGRATION_README.md) for details.
