-- Migration: Clean up location architecture
-- Remove backward compatibility cruft and migrate to beach-specific names
-- Author: Shahar + Claude
-- Date: 2026-02-07

-- ============================================================================
-- PHASE 1: Migrate old city names to new beach names
-- ============================================================================

-- Migrate users table
UPDATE users SET location = 'Bat Galim (Haifa)' WHERE location = 'Haifa, Israel';
UPDATE users SET location = 'Hilton Beach (Tel Aviv)' WHERE location = 'Tel Aviv, Israel';
UPDATE users SET location = 'Ashdod (Gil Beach)' WHERE location = 'Ashdod, Israel';
UPDATE users SET location = 'Sironit Beach (Netanya)' WHERE location = 'Netanya, Israel';
UPDATE users SET location = 'Olga Beach (Hadera)' WHERE location = 'Hadera, Israel';
UPDATE users SET location = 'Ashkelon (Marina)' WHERE location = 'Ashkelon, Israel';
UPDATE users SET location = 'Sokolov Beach (Nahariya)' WHERE location = 'Nahariya, Israel';
UPDATE users SET location = 'Zikim Beach' WHERE location = 'Eilat, Israel';

-- Migrate arduinos table
UPDATE arduinos SET location = 'Bat Galim (Haifa)' WHERE location = 'Haifa, Israel';
UPDATE arduinos SET location = 'Hilton Beach (Tel Aviv)' WHERE location = 'Tel Aviv, Israel';
UPDATE arduinos SET location = 'Ashdod (Gil Beach)' WHERE location = 'Ashdod, Israel';
UPDATE arduinos SET location = 'Sironit Beach (Netanya)' WHERE location = 'Netanya, Israel';
UPDATE arduinos SET location = 'Olga Beach (Hadera)' WHERE location = 'Hadera, Israel';
UPDATE arduinos SET location = 'Ashkelon (Marina)' WHERE location = 'Ashkelon, Israel';
UPDATE arduinos SET location = 'Sokolov Beach (Nahariya)' WHERE location = 'Nahariya, Israel';
UPDATE arduinos SET location = 'Zikim Beach' WHERE location = 'Eilat, Israel';

-- ============================================================================
-- PHASE 2: Delete old city-based location entries
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
-- PHASE 3: Mark URL columns as deprecated (remove in future migration)
-- ============================================================================

-- NOTE: Not dropping columns yet - will verify system works first
-- Future migration: ALTER TABLE locations DROP COLUMN wave_api_url;
-- Future migration: ALTER TABLE locations DROP COLUMN wind_api_url;

COMMENT ON COLUMN locations.wave_api_url IS 'DEPRECATED - URLs computed from beaches.py, will be removed';
COMMENT ON COLUMN locations.wind_api_url IS 'DEPRECATED - URLs computed from beaches.py, will be removed';

-- ============================================================================
-- Verification queries (run after migration)
-- ============================================================================

-- Check for any remaining old city names
-- SELECT * FROM users WHERE location LIKE '%, Israel';
-- SELECT * FROM arduinos WHERE location LIKE '%, Israel';
-- SELECT * FROM locations WHERE location LIKE '%, Israel';

-- Count locations per table
-- SELECT 'users' as table_name, COUNT(DISTINCT location) as location_count FROM users
-- UNION ALL
-- SELECT 'arduinos', COUNT(DISTINCT location) FROM arduinos
-- UNION ALL
-- SELECT 'locations', COUNT(*) FROM locations;
