-- Add request_interval_minutes column to arduinos table
ALTER TABLE arduinos ADD COLUMN IF NOT EXISTS request_interval_minutes INTEGER DEFAULT 13 NOT NULL;

-- Initial rollout: update all existing rows to 13 (though default handles new ones)
UPDATE arduinos SET request_interval_minutes = 13 WHERE request_interval_minutes IS NULL;
