-- Migration: Clean up location architecture
-- Remove backward compatibility cruft and migrate to beach-specific names
-- Author: Shahar + Claude
-- Date: 2026-02-07

-- ============================================================================
-- PHASE 1: Create new beach location entries (with empty URLs)
-- ============================================================================

-- Insert new beach locations (processor will populate surf data on next run)
-- Copy existing data from old city entries where available
INSERT INTO locations (location, wave_api_url, wind_api_url, wave_height_m, wave_period_s, wind_speed_mps, wind_direction_deg, wave_calculation_method)
SELECT
    'Bat Galim (Haifa)',
    '',  -- Empty URL (processor will ignore)
    '',
    COALESCE(wave_height_m, 0),
    COALESCE(wave_period_s, 0),
    COALESCE(wind_speed_mps, 0),
    COALESCE(wind_direction_deg, 0),
    'api'
FROM locations WHERE location = 'Haifa, Israel'
ON CONFLICT (location) DO NOTHING;

INSERT INTO locations (location, wave_api_url, wind_api_url, wave_height_m, wave_period_s, wind_speed_mps, wind_direction_deg, wave_calculation_method)
SELECT
    'Hilton Beach (Tel Aviv)',
    '',
    '',
    COALESCE(wave_height_m, 0),
    COALESCE(wave_period_s, 0),
    COALESCE(wind_speed_mps, 0),
    COALESCE(wind_direction_deg, 0),
    'api'
FROM locations WHERE location = 'Tel Aviv, Israel'
ON CONFLICT (location) DO NOTHING;

INSERT INTO locations (location, wave_api_url, wind_api_url, wave_height_m, wave_period_s, wind_speed_mps, wind_direction_deg, wave_calculation_method)
SELECT
    'Ashdod (Gil Beach)',
    '',
    '',
    COALESCE(wave_height_m, 0),
    COALESCE(wave_period_s, 0),
    COALESCE(wind_speed_mps, 0),
    COALESCE(wind_direction_deg, 0),
    'api'
FROM locations WHERE location = 'Ashdod, Israel'
ON CONFLICT (location) DO NOTHING;

INSERT INTO locations (location, wave_api_url, wind_api_url, wave_height_m, wave_period_s, wind_speed_mps, wind_direction_deg, wave_calculation_method)
SELECT
    'Sironit Beach (Netanya)',
    '',
    '',
    COALESCE(wave_height_m, 0),
    COALESCE(wave_period_s, 0),
    COALESCE(wind_speed_mps, 0),
    COALESCE(wind_direction_deg, 0),
    'api'
FROM locations WHERE location = 'Netanya, Israel'
ON CONFLICT (location) DO NOTHING;

INSERT INTO locations (location, wave_api_url, wind_api_url, wave_height_m, wave_period_s, wind_speed_mps, wind_direction_deg, wave_calculation_method)
SELECT
    'Olga Beach (Hadera)',
    '',
    '',
    COALESCE(wave_height_m, 0),
    COALESCE(wave_period_s, 0),
    COALESCE(wind_speed_mps, 0),
    COALESCE(wind_direction_deg, 0),
    'api'
FROM locations WHERE location = 'Hadera, Israel'
ON CONFLICT (location) DO NOTHING;

INSERT INTO locations (location, wave_api_url, wind_api_url, wave_height_m, wave_period_s, wind_speed_mps, wind_direction_deg, wave_calculation_method)
SELECT
    'Ashkelon (Marina)',
    '',
    '',
    COALESCE(wave_height_m, 0),
    COALESCE(wave_period_s, 0),
    COALESCE(wind_speed_mps, 0),
    COALESCE(wind_direction_deg, 0),
    'api'
FROM locations WHERE location = 'Ashkelon, Israel'
ON CONFLICT (location) DO NOTHING;

INSERT INTO locations (location, wave_api_url, wind_api_url, wave_height_m, wave_period_s, wind_speed_mps, wind_direction_deg, wave_calculation_method)
SELECT
    'Sokolov Beach (Nahariya)',
    '',
    '',
    COALESCE(wave_height_m, 0),
    COALESCE(wave_period_s, 0),
    COALESCE(wind_speed_mps, 0),
    COALESCE(wind_direction_deg, 0),
    'api'
FROM locations WHERE location = 'Nahariya, Israel'
ON CONFLICT (location) DO NOTHING;

INSERT INTO locations (location, wave_api_url, wind_api_url, wave_height_m, wave_period_s, wind_speed_mps, wind_direction_deg, wave_calculation_method)
SELECT
    'Zikim Beach',
    '',
    '',
    COALESCE(wave_height_m, 0),
    COALESCE(wave_period_s, 0),
    COALESCE(wind_speed_mps, 0),
    COALESCE(wind_direction_deg, 0),
    'api'
FROM locations WHERE location = 'Eilat, Israel'
ON CONFLICT (location) DO NOTHING;

-- ============================================================================
-- PHASE 2: Migrate users and arduinos to new beach names
-- ============================================================================

-- Now that locations exist, update foreign keys
UPDATE users SET location = 'Bat Galim (Haifa)' WHERE location = 'Haifa, Israel';
UPDATE users SET location = 'Hilton Beach (Tel Aviv)' WHERE location = 'Tel Aviv, Israel';
UPDATE users SET location = 'Ashdod (Gil Beach)' WHERE location = 'Ashdod, Israel';
UPDATE users SET location = 'Sironit Beach (Netanya)' WHERE location = 'Netanya, Israel';
UPDATE users SET location = 'Olga Beach (Hadera)' WHERE location = 'Hadera, Israel';
UPDATE users SET location = 'Ashkelon (Marina)' WHERE location = 'Ashkelon, Israel';
UPDATE users SET location = 'Sokolov Beach (Nahariya)' WHERE location = 'Nahariya, Israel';
UPDATE users SET location = 'Zikim Beach' WHERE location = 'Eilat, Israel';

UPDATE arduinos SET location = 'Bat Galim (Haifa)' WHERE location = 'Haifa, Israel';
UPDATE arduinos SET location = 'Hilton Beach (Tel Aviv)' WHERE location = 'Tel Aviv, Israel';
UPDATE arduinos SET location = 'Ashdod (Gil Beach)' WHERE location = 'Ashdod, Israel';
UPDATE arduinos SET location = 'Sironit Beach (Netanya)' WHERE location = 'Netanya, Israel';
UPDATE arduinos SET location = 'Olga Beach (Hadera)' WHERE location = 'Hadera, Israel';
UPDATE arduinos SET location = 'Ashkelon (Marina)' WHERE location = 'Ashkelon, Israel';
UPDATE arduinos SET location = 'Sokolov Beach (Nahariya)' WHERE location = 'Nahariya, Israel';
UPDATE arduinos SET location = 'Zikim Beach' WHERE location = 'Eilat, Israel';

-- ============================================================================
-- PHASE 3: Delete old city-based location entries
-- ============================================================================

DELETE FROM locations WHERE location = 'Haifa, Israel';
DELETE FROM locations WHERE location = 'Tel Aviv, Israel';
DELETE FROM locations WHERE location = 'Ashdod, Israel';
DELETE FROM locations WHERE location = 'Netanya, Israel';
DELETE FROM locations WHERE location = 'Hadera, Israel';
DELETE FROM locations WHERE location = 'Ashkelon, Israel';
DELETE FROM locations WHERE location = 'Nahariya, Israel';
DELETE FROM locations WHERE location = 'Eilat, Israel';

-- ============================================================================
-- PHASE 4: Mark URL columns as deprecated (remove in future migration)
-- ============================================================================

COMMENT ON COLUMN locations.wave_api_url IS 'DEPRECATED - URLs computed from beaches.py, will be removed';
COMMENT ON COLUMN locations.wind_api_url IS 'DEPRECATED - URLs computed from beaches.py, will be removed';
