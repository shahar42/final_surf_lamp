# Location Integration Plan: From Cities to Beaches

## Objective
Transition the Surf Lamp system from a city-based location model (e.g., "Tel Aviv") to a granular, beach-based model (e.g., "Hilton Beach") and enhance data reliability with Stormglass integration.

## Phase 1: Data & Configuration Refactor
1.  **Create `utils/location_manager.py`**: Extract all location-related logic (timezones, coordinates, API mapping) from `shared_config.py` and `data_base.py` into this new module.
2.  **Update `location_endpoints.json`**:
    *   Populate with all 27 beaches from `israel_beaches.md`.
    *   Add **Stormglass** as the Priority 1 (or +1) endpoint for all beaches.
    *   Retain Open-Meteo and Isramar as fallback/secondary sources.
3.  **Coordinate Mapping**: Ensure `LOCATION_COORDS` in `blueprints/api_arduino.py` is updated to include beach-level precision.

## Phase 2: Database Migration
1.  **Populate `locations` table**: Run a migration script to insert the 27 new beach records.
2.  **Mapping Legacy Locations**: Create a mapping for existing users (e.g., "Tel Aviv" -> "Gordon Beach") to prevent system breakage during transition.
3.  **Schema Check**: Ensure the `location` column in `users` and `arduinos` tables can handle Hebrew characters and longer beach names.

## Phase 3: Backend API Enhancements
1.  **Search API**: Implement a new endpoint `/api/locations/search?q=...` that performs fuzzy matching across English and Hebrew beach names.
2.  **Validation Logic**: Update `forms.py` and `api_user.py` to validate against the new beach list instead of the hardcoded `SURF_LOCATIONS` list.
3.  **Stormglass Integration**: Add the Stormglass API key to environment variables and update `weather_api_client.py` to handle Stormglass's specific JSON structure.

## Phase 4: Frontend UI/UX (Adam Wathan Style)
1.  **Searchable Input**: Replace the `SelectField` dropdown in the dashboard with a custom, searchable UI component.
2.  **Bilingual Support**: Ensure the search component filters by both Hebrew and English names simultaneously.
3.  **Responsive Design**: Ensure the search dropdown works seamlessly on mobile devices (Bottom Nav "Location" tab).

## Phase 5: Background Processor Scaling
1.  **Batch Processing**: Update `background_processor.py` to handle 27+ locations. Consider parallel fetching if sequential updates take too long.
2.  **Rate Limit Management**: Monitor Stormglass API usage carefully (Stormglass often has strict daily limits).
3.  **Data Staleness**: Ensure the staleness tracking logic handles the higher frequency of updates across more locations.

## Verification Steps
*   Run `check_beach_conditions.py` to verify all new beach endpoints are responsive.
*   Unit test the fuzzy search logic.
*   Verify lamp behavior with beach-level coordinates for autonomous sunset calculation.
