# Analysis of API Calls in the Surf Lamp System

This document summarizes the locations where API calls are made, defined, and configured throughout the project.

## 1. External API Calls (Consuming 3rd Party Data)

These files are responsible for fetching data from external weather and surf forecast providers.

-   **`surf-lamp-processor/background_processor.py`**: This is the primary service for fetching external data. It uses the `requests` library to call API endpoints stored in the database. The logic handles multiple data sources with a priority system.
    -   **Key APIs Mentioned:** OpenWeatherMap, Open-Meteo, Isramar.
-   **`api_TESTING/`**: This directory contains several scripts for testing and discovering external API endpoints.
    -   `find_more.py`: Tests `MARINE_API_URL` and `FORECAST_API_URL`.
    -   `find_cali_points.py`: Tests various endpoints for Californian cities from Open-Meteo, Spitcast, Stormglass, and XWeather.
    -   `display_surf_conditions.py`: Fetches data from a list of pre-defined endpoints.
-   **`surf-lamp-processor/fix_wind_endpoints.sql`**: This SQL script directly updates `http_endpoint` values in the database, replacing Open-Meteo URLs with OpenWeatherMap URLs.

## 2. Internal API Calls (Service-to-Service)

These are calls between components within the surf lamp system.

-   **Frontend to Backend:**
    -   Files in `web_and_database/templates/` (e.g., `dashboard.html`, `experimental_dashboard.html`) use the browser's `fetch()` API to call backend endpoints like `/update-location`, `/update-theme`, and `/api/arduino/${arduinoId}/data`.
-   **Arduino to Backend:**
    -   The physical Arduino device (and the `arduino_sim.py` simulator) calls the `/api/arduino/{id}/data` endpoint to get its surf data.
-   **Testing Scripts:**
    -   `test_pull_endpoints.py`: Specifically tests the `/api/discovery/server` and `/api/arduino/{id}/data` endpoints.
    -   `test_discovery_system.py`: Tests the discovery endpoint.

## 3. API Endpoint Definitions (Providing APIs)

These files define the API endpoints that other services consume.

-   **`web_and_database/app.py`**: The main Flask application. It defines all the backend endpoints for the web dashboard and the Arduino devices.
    -   e.g., `/update-location`, `/update-theme`, `/api/arduino/<int:arduino_id>/data`, `/api/discovery/server`.
-   **`arduino/arduinomain_lamp.ino`**: The C++ code for the ESP32. It runs its own local web server and defines several endpoints for debugging and local control, such as `/api/status`, `/api/fetch`, and `/api/led-test`.
-   **`surf-lamp-visualizer/app.py`**: A Flask app that provides visualization endpoints like `/api/system-data` and `/api/stats`.

## 4. API Configuration

These files are crucial for managing how and where API calls are made.

-   **`surf-lamp-processor/endpoint_configs.py`**: This is a key configuration file. It contains Python dictionaries that map the fields from different external API responses to a standardized internal format. This allows the `background_processor` to handle data from various sources.
-   **`web_and_database/data_base.py`**: Defines the database schema. The `usage_lamps` table is critical, as it stores the `http_endpoint` and `api_key` for each lamp's data sources.
-   **`discovery-config/config.json`**: Contains a JSON structure for server discovery, allowing the Arduino to find the correct backend server address dynamically.

## 5. Database Interactions (Asyncpg/Supabase)

-   **`mcp-supabase-server/fastmcp_supabase_server.py`**: The `conn.fetch(...)` calls in this file are **not** HTTP API calls. They are asynchronous database queries to a Supabase (PostgreSQL) database using a library like `asyncpg`. While it acts as a data access layer, it's distinct from the REST/HTTP APIs found elsewhere.

## 6. Other Notable Files

-   **`surf_lamp_monitor.py`**: Makes a `POST` request to a Discord webhook for sending alerts.
-   **`render-mcp-server/deploy_tools.py`**: Makes calls to the Render API (`https://api.render.com`) to manage deployments.
