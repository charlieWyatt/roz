-- Migration 002: Add data retention policy
-- Created: 2025-10-25
-- Description: Adds retention settings and cleanup functions

-- Function to delete old heatmap data
CREATE OR REPLACE FUNCTION cleanup_old_heatmaps(retention_days INT DEFAULT 90)
RETURNS TABLE(deleted_count BIGINT) AS $$
DECLARE
    cutoff_date TIMESTAMPTZ;
    rows_deleted BIGINT;
BEGIN
    cutoff_date := NOW() - (retention_days || ' days')::INTERVAL;
    
    DELETE FROM heatmap_minutes
    WHERE timestamp < cutoff_date;
    
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    
    RETURN QUERY SELECT rows_deleted;
END;
$$ LANGUAGE plpgsql;

-- Optional: Add a retention policy column to track per-camera settings
ALTER TABLE heatmap_minutes 
ADD COLUMN IF NOT EXISTS retention_days INT DEFAULT 90;

-- Comment for documentation
COMMENT ON FUNCTION cleanup_old_heatmaps IS 'Deletes heatmap data older than specified days. Run periodically via cron or pg_cron.';

-- Example cron job (requires pg_cron extension):
-- SELECT cron.schedule('cleanup-heatmaps', '0 2 * * *', $$SELECT cleanup_old_heatmaps(90)$$);

