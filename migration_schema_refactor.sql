-- ============================================================
-- SURF LAMP SCHEMA REFACTOR MIGRATION
-- Location-centric architecture with per-arduino location override
-- ============================================================

-- STEP 1: Create new locations table
-- ============================================================
CREATE TABLE locations (
    location VARCHAR(255) PRIMARY KEY,
    wave_api_url TEXT NOT NULL,
    wind_api_url TEXT NOT NULL,
    wave_height_m DOUBLE PRECISION,
    wave_period_s DOUBLE PRECISION,
    wind_speed_mps DOUBLE PRECISION,
    wind_direction_deg INTEGER,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- STEP 2: Populate locations table with API endpoints from existing data
-- ============================================================
-- Extract unique location + endpoint pairs (priority 1 = waves, priority 2 = wind)
INSERT INTO locations (location, wave_api_url, wind_api_url)
SELECT DISTINCT
    u.location,
    MAX(CASE WHEN ul.endpoint_priority = 1 THEN ul.http_endpoint END) AS wave_api_url,
    MAX(CASE WHEN ul.endpoint_priority = 2 THEN ul.http_endpoint END) AS wind_api_url
FROM users u
LEFT JOIN lamps l ON l.user_id = u.user_id
LEFT JOIN usage_lamps ul ON ul.lamp_id = l.lamp_id
GROUP BY u.location
HAVING MAX(CASE WHEN ul.endpoint_priority = 1 THEN ul.http_endpoint END) IS NOT NULL
   AND MAX(CASE WHEN ul.endpoint_priority = 2 THEN ul.http_endpoint END) IS NOT NULL;

-- STEP 3: Migrate current_conditions data to locations table
-- ============================================================
-- Aggregate conditions by location (use most recent data per location)
UPDATE locations loc
SET
    wave_height_m = subq.wave_height_m,
    wave_period_s = subq.wave_period_s,
    wind_speed_mps = subq.wind_speed_mps,
    wind_direction_deg = subq.wind_direction_deg,
    last_updated = subq.last_updated
FROM (
    SELECT
        u.location,
        cc.wave_height_m,
        cc.wave_period_s,
        cc.wind_speed_mps,
        cc.wind_direction_deg,
        cc.last_updated,
        ROW_NUMBER() OVER (PARTITION BY u.location ORDER BY cc.last_updated DESC) AS rn
    FROM current_conditions cc
    JOIN lamps l ON cc.lamp_id = l.lamp_id
    JOIN users u ON l.user_id = u.user_id
) subq
WHERE loc.location = subq.location AND subq.rn = 1;

-- STEP 4: Create new arduinos table
-- ============================================================
CREATE TABLE arduinos (
    arduino_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    location VARCHAR(255) NOT NULL REFERENCES locations(location) ON DELETE RESTRICT,
    last_poll_time TIMESTAMP DEFAULT NOW()
);

-- STEP 5: Migrate data from lamps to arduinos
-- ============================================================
INSERT INTO arduinos (arduino_id, user_id, location, last_poll_time)
SELECT
    l.arduino_id,
    l.user_id,
    u.location,
    l.last_updated
FROM lamps l
JOIN users u ON l.user_id = u.user_id;

-- STEP 6: Update error_reports to use arduino_id
-- ============================================================
ALTER TABLE error_reports
    DROP CONSTRAINT IF EXISTS error_reports_lamp_id_fkey;

ALTER TABLE error_reports
    DROP COLUMN IF EXISTS lamp_id;

-- Add foreign key constraint to arduinos table
ALTER TABLE error_reports
    ADD CONSTRAINT error_reports_arduino_id_fkey
    FOREIGN KEY (arduino_id) REFERENCES arduinos(arduino_id) ON DELETE SET NULL;

-- STEP 7: Drop old tables
-- ============================================================
DROP TABLE IF EXISTS current_conditions CASCADE;
DROP TABLE IF EXISTS usage_lamps CASCADE;
DROP TABLE IF EXISTS location_websites CASCADE;
DROP TABLE IF EXISTS daily_usage CASCADE;
DROP TABLE IF EXISTS lamps CASCADE;

-- STEP 8: Verify migration
-- ============================================================
-- Run these queries to verify data integrity:
-- SELECT COUNT(*) FROM locations;
-- SELECT COUNT(*) FROM arduinos;
-- SELECT a.arduino_id, a.user_id, a.location, u.username FROM arduinos a JOIN users u ON a.user_id = u.user_id;
-- SELECT location, wave_api_url, wind_api_url FROM locations;

-- ============================================================
-- MIGRATION COMPLETE
-- New architecture:
-- - users.location = dashboard default view
-- - arduinos.location = where this specific arduino fetches data
-- - locations table = one API call per location (location-centric)
-- ============================================================
