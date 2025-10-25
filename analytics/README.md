# Foot Traffic Heatmap Generator

Automatically generates foot traffic heatmaps from surveillance videos stored in S3/Cloudflare R2.

## How It Works

Uses background subtraction to detect motion and creates a heatmap showing where the most activity occurs in your videos.

## Quick Start

### 1. Install

```bash
cd /Users/charliewyatt/Documents/projects/roz/analytics
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
python heatmapper_worker.py --prefix "2025/10/20/"
```

Limit number of videos:

```bash
python heatmapper_worker.py --max-videos 5
```

## File Structure

```
analytics/
├── db_helpers.py          # S3 operations
├── heatmap_helpers.py     # Heatmap generation
├── heatmapper_worker.py   # Main worker script
├── config.py              # Configuration
└── requirements.txt       # Dependencies
```

## Configuration

Edit `.env` file:

- **S3_ACCESS_KEY** / **S3_SECRET_KEY**: Your S3 credentials (required)
- **VIDEO_PREFIX**: Filter videos by path (e.g., "2025/10/20/")
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

## S3 Structure

Videos:

```
2025/10/20/13/clip_2025-10-20_13-57-04.mp4
```

Heatmaps (auto-generated):

```
2025/10/20/13/clip_2025-10-20_13-57-04_heatmap.jpg
```

## Dependencies

- **boto3**: S3 operations
- **opencv-python**: Video processing
- **numpy**: Array operations
- **matplotlib**: Heatmap visualization
