-- Migration 001: Initial heatmap schema
-- Created: 2025-10-25
-- Description: Creates the core heatmap_minutes table for storing per-minute motion intensity data

-- Enable TimescaleDB extension (optional but recommended)
-- CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Main table for storing heatmap data per minute
CREATE TABLE IF NOT EXISTS heatmap_minutes (
    id BIGSERIAL PRIMARY KEY,
    
    -- Time & Camera identification
    camera_id VARCHAR(50) NOT NULL DEFAULT 'default',
    timestamp TIMESTAMPTZ NOT NULL,  -- Start time of this minute
    
    -- Video source (for traceability back to S3)
    video_path TEXT NOT NULL,  -- S3 key: raw_videos/2025/10/20/video.mp4
    
    -- Heatmap dimensions
    height INT NOT NULL,  -- Downscaled height (e.g., 270)
    width INT NOT NULL,   -- Downscaled width (e.g., 480)
    downscale_factor REAL NOT NULL DEFAULT 0.25,
    
    -- The actual heatmap data: 2D array of float32 intensity values
    -- Stored as compressed binary (zlib compressed numpy array)
    intensity_array BYTEA NOT NULL,
    
    -- Statistics for quick filtering and analysis
    frame_count INT NOT NULL,  -- Number of frames processed in this minute
    total_intensity REAL NOT NULL,  -- Sum of all intensity values (activity metric)
    max_intensity REAL NOT NULL,  -- Maximum intensity value in array
    nonzero_pixels INT NOT NULL,  -- Number of pixels with motion detected
    
    -- Metadata
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure we don't duplicate data for same camera/time
    CONSTRAINT unique_camera_minute UNIQUE(camera_id, timestamp)
);

-- Essential indexes for fast queries
CREATE INDEX idx_heatmap_camera_time ON heatmap_minutes(camera_id, timestamp DESC);
CREATE INDEX idx_heatmap_time ON heatmap_minutes(timestamp DESC);

-- Index for finding busy/quiet periods
CREATE INDEX idx_heatmap_activity ON heatmap_minutes(camera_id, total_intensity DESC);

-- Index for video path lookups (traceability)
CREATE INDEX idx_heatmap_video_path ON heatmap_minutes(video_path);

-- Composite index for common time range queries
CREATE INDEX idx_heatmap_camera_time_range ON heatmap_minutes(camera_id, timestamp DESC, total_intensity);

-- Optional: Convert to TimescaleDB hypertable for better time-series performance
-- Uncomment if you installed TimescaleDB extension
-- SELECT create_hypertable('heatmap_minutes', 'timestamp', 
--     if_not_exists => TRUE,
--     migrate_data => TRUE
-- );

-- Optional: Enable compression for older data (uncomment if using TimescaleDB)
-- ALTER TABLE heatmap_minutes SET (
--     timescaledb.compress,
--     timescaledb.compress_segmentby = 'camera_id',
--     timescaledb.compress_orderby = 'timestamp DESC'
-- );

-- Optional: Auto-compress data older than 7 days (uncomment if using TimescaleDB)
-- SELECT add_compression_policy('heatmap_minutes', INTERVAL '7 days');

-- Create a view for easy statistics queries
CREATE OR REPLACE VIEW heatmap_stats AS
SELECT 
    camera_id,
    DATE_TRUNC('hour', timestamp) as hour,
    COUNT(*) as minute_count,
    SUM(total_intensity) as total_activity,
    AVG(total_intensity) as avg_activity,
    MAX(max_intensity) as peak_intensity,
    SUM(frame_count) as total_frames
FROM heatmap_minutes
GROUP BY camera_id, DATE_TRUNC('hour', timestamp);

-- Comments for documentation
COMMENT ON TABLE heatmap_minutes IS 'Stores per-minute heatmap intensity data from video analysis';
COMMENT ON COLUMN heatmap_minutes.intensity_array IS 'Compressed numpy float32 array (height x width) of motion intensity values';
COMMENT ON COLUMN heatmap_minutes.total_intensity IS 'Quick metric for activity level - sum of all intensity values';
COMMENT ON COLUMN heatmap_minutes.video_path IS 'S3 key of source video for traceability';

