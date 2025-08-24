# Surf Lamp Processor

This is the backend data processing engine for the Surf Lamp project. It runs as a persistent background service, responsible for fetching real-time surf and weather data from various APIs, standardizing it, and sending it to the Surf Lamp Arduino devices.

## Key Features

*   **Multi-API Support:** Aggregates data from multiple sources (e.g., OpenWeatherMap, Open-Meteo, Isramar) to create a complete surf report.
*   **Database Driven:** All configurations, including API endpoints, lamp locations, and user preferences, are managed through a central PostgreSQL database.
*   **Data Standardization:** A flexible configuration system (`endpoint_configs.py`) maps disparate API responses into a consistent, standardized format.
*   **Resilient Communication:** Implements a failure-tracking mechanism that temporarily suspends communication with unresponsive Arduino devices to improve overall system stability.
*   **Mock Transport Layer:** Includes a mock communication layer for development and testing without requiring a physical Arduino device.

## How It Works

The processor runs in a continuous loop with the following workflow:

1.  **Fetch Lamp Configurations:** Retrieves a list of all active lamps and their associated API configurations from the database.
2.  **Fetch Surf Data:** For each lamp, it calls the configured APIs in order of priority.
3.  **Standardize Data:** The raw JSON data from each API is processed and mapped to a standard set of fields (e.g., `wave_height_m`, `wind_speed_mps`).
4.  **Update Database:** The latest conditions are stored in the `current_conditions` table for use by the web dashboard.
5.  **Send to Arduino:** The final, processed data payload is sent to the corresponding Arduino device via an HTTP POST request.

## Setup and Running

### 1. Dependencies

Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

This service is configured using environment variables. Create a `.env` file in this directory or set the variables directly in your shell.

| Variable              | Description                                                                                             | Default   | Example                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------------- | --------- | --------------------------------------------------------------------- |
| `DATABASE_URL`        | **Required.** The connection string for the PostgreSQL database.                                        | (None)    | `postgresql://user:pass@host:port/dbname`                             |
| `ARDUINO_TRANSPORT`   | The transport to use for Arduino communication. Set to `mock` for development.                          | `http`    | `mock`                                                                |
| `TEST_MODE`           | If `true`, the script will run the processing cycle once and then exit.                                 | `false`   | `true`                                                                |

### 3. Running the Processor

To run the processor in standard (continuous) mode:

```bash
python background_processor.py
```

The service will run the processing cycle immediately upon starting and then every 30 minutes thereafter.

To run in test mode for a single execution cycle:

```bash
TEST_MODE=true python background_processor.py
```

## Configuration

### Endpoint Configuration

To add support for a new data API, you need to:

1.  Add a new entry in the `FIELD_MAPPINGS` dictionary in `endpoint_configs.py`.
2.  Define the paths to the required data fields within the API's JSON response.
3.  If necessary, add a custom conversion or extraction function.

### Arduino Transport

The `ARDUINO_TRANSPORT` environment variable controls how the processor communicates with the Arduino:

*   `http` (default): Sends real HTTP POST requests to the Arduino's IP address.
*   `mock`: Simulates the request and logs the payload to the console. This is useful for debugging the data processing logic without a physical device.
