# Roz Heatmap Analytics

Database-backed surveillance video analytics. Processes videos minute-by-minute and stores motion heatmap data in PostgreSQL.

## Quick Setup

### 1. Install Dependencies

```bash
poetry install
```

### 2. Configure (create `.env` in project root)

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=roz
DB_USER=YOUR_USERNAME
DB_PASSWORD=YOUR_PASSWORD

# S3 Credentials
S3_ACCESS_KEY=your_key
S3_SECRET_KEY=your_secret
S3_BUCKET_NAME=roz
```

### 3. Run Migrations

```bash
poetry run python db/migrate.py
```

### 4. Process Videos

```bash
poetry run python analytics/heatmapper_worker.py --max-videos 1
```

## Commands

```bash
# Show database stats
poetry run python analytics/heatmapper_worker.py --stats

# Process specific date
poetry run python analytics/heatmapper_worker.py --date-prefix "2025/10/20/"

# Generate image from database
poetry run python analytics/generate_heatmap_image.py --hours 24 --output heatmap.jpg
```

## How It Works

1. Videos downloaded from S3 (`raw_videos/2025/10/20/clip_2025-10-20_14-08-00.mp4`)
2. Processed minute-by-minute using motion detection
3. Each minute stored as compressed array in PostgreSQL
4. Query any time range to generate heatmaps dynamically

## Database Schema

See `db/README.md` for schema details and SQL queries.
