-- Migration: Add Redis Health Monitoring Tables
-- Purpose: Track Redis health status and service health history for fallback mechanism
-- Date: 2026-02-07

-- Redis health monitoring table
CREATE TABLE IF NOT EXISTS redis_health (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL UNIQUE,
    last_success_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_failure_timestamp TIMESTAMPTZ,
    consecutive_failures INTEGER DEFAULT 0,
    total_failures_24h INTEGER DEFAULT 0,
    is_healthy BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_redis_health_service ON redis_health(service_name);

-- Initialize entries for web service and background processor
INSERT INTO redis_health (service_name) VALUES
    ('web-service'),
    ('background-processor')
ON CONFLICT (service_name) DO NOTHING;

-- Service health history table for long-term monitoring
CREATE TABLE IF NOT EXISTS service_health_history (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    service_type VARCHAR(50) NOT NULL,  -- 'redis', 'database', 'processor'
    status VARCHAR(20) NOT NULL,        -- 'healthy', 'degraded', 'down'
    latency_ms INTEGER,
    error_message TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_health_history_timestamp ON service_health_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_health_history_service ON service_health_history(service_name, timestamp DESC);

-- Add comment for documentation
COMMENT ON TABLE redis_health IS 'Tracks Redis connection health status for web and background services';
COMMENT ON TABLE service_health_history IS 'Historical log of service health events (7-day retention)';
