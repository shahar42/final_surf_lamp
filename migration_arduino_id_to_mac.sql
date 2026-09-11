-- Change the lamp identifier from an integer to the lamp's MAC address.
--
-- A lamp is now identified by its factory MAC, stored as 12 lowercase hex
-- digits ("a4cf12345678"). Nothing is derived from it: the lamp sends that
-- string in its request URL, the user pastes the same address at
-- registration, and the dashboard shows it back.
--
-- Lamps already in the field keep their small programmer-assigned numbers,
-- which simply become the decimal string ("8", "14"). Their firmware keeps
-- requesting the same URL, so NO DEVICE NEEDS A VISIT.
--
-- This alters a primary key and the foreign key pointing at it, so run it in
-- a maintenance window with the web service and processor stopped. It is
-- wrapped in a transaction: if any statement fails, nothing changes.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migration_arduino_id_to_mac.sql
--
-- Rollback is at the bottom of this file.

BEGIN;

-- 1. Drop the FK so the two columns can change type independently.
ALTER TABLE error_reports
    DROP CONSTRAINT IF EXISTS error_reports_arduino_id_fkey;

-- 2. Widen both columns to text. USING makes the existing integers their
--    decimal strings, which is exactly the legacy identifier we want.
ALTER TABLE arduinos
    ALTER COLUMN arduino_id TYPE VARCHAR(12) USING arduino_id::text;

ALTER TABLE error_reports
    ALTER COLUMN arduino_id TYPE VARCHAR(12) USING arduino_id::text;

-- 3. Restore the FK.
ALTER TABLE error_reports
    ADD CONSTRAINT error_reports_arduino_id_fkey
    FOREIGN KEY (arduino_id) REFERENCES arduinos(arduino_id);

-- 4. Guard the format at the database level so a malformed identifier can
--    never be stored: either 12 lowercase hex digits (a MAC) or a legacy
--    decimal with no leading zeros.
ALTER TABLE arduinos
    ADD CONSTRAINT arduinos_arduino_id_format
    CHECK (arduino_id ~ '^([0-9a-f]{12}|[1-9][0-9]{0,7})$');

COMMIT;

-- Verify:
--   SELECT arduino_id, pg_typeof(arduino_id) FROM arduinos ORDER BY arduino_id;
--
-- Rollback (only valid while every arduino_id is still numeric, i.e. before
-- any MAC-identified lamp has registered):
--
--   BEGIN;
--   ALTER TABLE error_reports DROP CONSTRAINT error_reports_arduino_id_fkey;
--   ALTER TABLE arduinos DROP CONSTRAINT arduinos_arduino_id_format;
--   ALTER TABLE arduinos ALTER COLUMN arduino_id TYPE INTEGER USING arduino_id::integer;
--   ALTER TABLE error_reports ALTER COLUMN arduino_id TYPE INTEGER USING arduino_id::integer;
--   ALTER TABLE error_reports ADD CONSTRAINT error_reports_arduino_id_fkey
--       FOREIGN KEY (arduino_id) REFERENCES arduinos(arduino_id);
--   COMMIT;
