-- Migration: Add processor_heartbeat table for watchdog monitoring
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS processor_heartbeat (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL UNIQUE,
    last_alive_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    missed_count INTEGER DEFAULT 0,
    revive_count INTEGER DEFAULT 0,
    max_revives INTEGER DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert initial record for the processor
INSERT INTO processor_heartbeat (service_name, last_alive_timestamp)
VALUES ('surf-lamp-processor', NOW())
ON CONFLICT (service_name) DO NOTHING;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_processor_heartbeat_service ON processor_heartbeat(service_name);

-- Verify creation
SELECT * FROM processor_heartbeat;
