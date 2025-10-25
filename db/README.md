# Database Schema

This directory contains the database schema and migrations for the Roz surveillance analytics system.

## Structure

```
db/
├── migrations/           # SQL migration files (run in order)
│   ├── 001_initial_schema.sql
│   └── 002_add_retention_policy.sql
├── migrate.py           # Python migration runner
├── schema.sql           # Current full schema (auto-generated)
├── .env.example         # Database configuration template
└── README.md            # This file
```

## Quick Start

### 1. Setup PostgreSQL

Install PostgreSQL:

```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# Ubuntu
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. Create Database User

```bash
# Connect to PostgreSQL
psql postgres

# Create user and database
CREATE USER roz_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE roz OWNER roz_user;
GRANT ALL PRIVILEGES ON DATABASE roz TO roz_user;
\q
```

### 3. Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit with your settings
nano .env
```

### 4. Run Migrations

```bash
# From project root
python db/migrate.py
```

Or with Poetry:

```bash
poetry run python db/migrate.py
```

## Database Schema

### Main Table: `heatmap_minutes`

Stores per-minute heatmap intensity data from video analysis.

| Column             | Type        | Description                              |
| ------------------ | ----------- | ---------------------------------------- |
| `id`               | BIGSERIAL   | Primary key                              |
| `camera_id`        | VARCHAR(50) | Camera identifier                        |
| `timestamp`        | TIMESTAMPTZ | Start of minute                          |
| `video_path`       | TEXT        | S3 key of source video                   |
| `height`           | INT         | Heatmap height (downscaled)              |
| `width`            | INT         | Heatmap width (downscaled)               |
| `downscale_factor` | REAL        | Downscale factor used                    |
| `intensity_array`  | BYTEA       | Compressed numpy array (zlib)            |
| `frame_count`      | INT         | Number of frames processed               |
| `total_intensity`  | REAL        | Sum of all intensities (activity metric) |
| `max_intensity`    | REAL        | Maximum intensity value                  |
| `nonzero_pixels`   | INT         | Pixels with motion detected              |
| `processed_at`     | TIMESTAMPTZ | When this was processed                  |

### Indexes

- `idx_heatmap_camera_time`: Fast camera + time range queries
- `idx_heatmap_time`: Time-based queries
- `idx_heatmap_activity`: Find busy/quiet periods
- `idx_heatmap_video_path`: Trace back to source video

### View: `heatmap_stats`

Pre-aggregated hourly statistics for quick dashboards.

## Data Format

### Intensity Array

The `intensity_array` column stores a compressed 2D numpy array:

```python
# Original numpy array (float32)
heatmap = np.zeros((270, 480), dtype=np.float32)  # Downscaled from 1080p

# Compress for storage
compressed = zlib.compress(heatmap.tobytes())

# Store in database
INSERT INTO heatmap_minutes (intensity_array, ...) VALUES (compressed, ...)

# Later: Decompress
decompressed = zlib.decompress(compressed_bytes)
heatmap = np.frombuffer(decompressed, dtype=np.float32).reshape(270, 480)
```

### Storage Size

- **Raw array**: 270 × 480 × 4 bytes = 518 KB
- **Compressed**: ~50-100 KB (typical)
- **Per day**: ~72-144 MB (1440 minutes)
- **Per month**: ~2-4 GB
- **Per year**: ~25-50 GB

## Common Queries

### 1. Get heatmap for last hour

```sql
SELECT intensity_array, height, width
FROM heatmap_minutes
WHERE camera_id = 'default'
  AND timestamp >= NOW() - INTERVAL '1 hour'
ORDER BY timestamp;
```

### 2. Find busiest hours today

```sql
SELECT
    DATE_TRUNC('hour', timestamp) as hour,
    SUM(total_intensity) as activity
FROM heatmap_minutes
WHERE camera_id = 'default'
  AND timestamp >= DATE_TRUNC('day', NOW())
GROUP BY hour
ORDER BY activity DESC;
```

### 3. Average pattern for 2pm across last 7 days

```sql
SELECT intensity_array, height, width
FROM heatmap_minutes
WHERE camera_id = 'default'
  AND EXTRACT(HOUR FROM timestamp) = 14
  AND timestamp >= NOW() - INTERVAL '7 days';
```

### 4. Check data freshness

```sql
SELECT
    camera_id,
    MAX(timestamp) as last_data,
    NOW() - MAX(timestamp) as age,
    COUNT(*) as total_minutes
FROM heatmap_minutes
GROUP BY camera_id;
```

## TimescaleDB (Optional)

For better time-series performance, enable TimescaleDB:

```sql
-- Enable extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Convert to hypertable (uncomment in migration)
SELECT create_hypertable('heatmap_minutes', 'timestamp');

-- Enable compression
ALTER TABLE heatmap_minutes SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'camera_id'
);

-- Auto-compress data older than 7 days
SELECT add_compression_policy('heatmap_minutes', INTERVAL '7 days');
```

## Maintenance

### Cleanup Old Data

```sql
-- Manual cleanup
SELECT cleanup_old_heatmaps(90);  -- Delete data older than 90 days

-- Check data size
SELECT
    pg_size_pretty(pg_total_relation_size('heatmap_minutes')) as total_size,
    COUNT(*) as row_count
FROM heatmap_minutes;
```

### Vacuum and Analyze

```sql
-- After large deletions
VACUUM ANALYZE heatmap_minutes;
```

## For TypeScript/Kysely

Your TypeScript app can:

1. **Use the same migrations**: Kysely can read these SQL files
2. **Generate types**: Use `kysely-codegen` to generate TypeScript types from the live database
3. **Write migrations**: Add new `.sql` files or use Kysely's migration system

Example Kysely setup:

```typescript
import { Kysely, PostgresDialect } from "kysely";
import { Pool } from "pg";

const db = new Kysely<Database>({
	dialect: new PostgresDialect({
		pool: new Pool({
			connectionString: process.env.DATABASE_URL,
		}),
	}),
});
```

## Backup

### Export data

```bash
pg_dump -U roz_user roz > backup.sql
```

### Restore data

```bash
psql -U roz_user roz < backup.sql
```

## Troubleshooting

### Connection refused

- Check PostgreSQL is running: `pg_isready`
- Check port: `lsof -i :5432`
- Check pg_hba.conf for auth settings

### Permission denied

- Ensure user has correct permissions: `GRANT ALL ON DATABASE roz TO roz_user`

### Slow queries

- Check indexes: `EXPLAIN ANALYZE SELECT ...`
- Consider TimescaleDB for time-series optimization
- Add composite indexes for your most common queries
