-- ============================================================
-- ADD RANGE ALERT FEATURE - MAX THRESHOLD COLUMNS
-- Enables range-based alerts (e.g., alert when waves 1m-3m)
-- ============================================================

ALTER TABLE users
ADD COLUMN wave_threshold_max_m DOUBLE PRECISION DEFAULT NULL;

ALTER TABLE users
ADD COLUMN wind_threshold_max_knots DOUBLE PRECISION DEFAULT NULL;

-- Verification
-- SELECT user_id, username, wave_threshold_m, wave_threshold_max_m, wind_threshold_knots, wind_threshold_max_knots FROM users LIMIT 5;
