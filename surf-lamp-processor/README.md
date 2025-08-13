# Surf Lamp Background Processor

This project is a background service that fetches surf data from various external APIs and sends it to Arduino-powered surf lamps. The service is designed to be highly configurable and extensible, allowing for the easy addition of new data sources and lamp types.

## Architecture

The system consists of a background processor that continuously performs the following steps:

1.  **Fetches API Configurations**: Retrieves a list of unique API endpoints and their configurations from a PostgreSQL database.
2.  **Fetches Surf Data**: Makes HTTP requests to the configured API endpoints to fetch the latest surf data.
3.  **Standardizes Data**: Parses the JSON responses from the APIs and transforms them into a standardized format using a data-driven mapping system.
4.  **Sends Data to Arduinos**: Sends the standardized surf data to the appropriate Arduino devices via HTTP POST requests.
5.  **Logs Everything**: Maintains a detailed log of all operations, errors, and successes in `lamp_processor.log`.

The data flow is as follows:

```
PostgreSQL Database -> Background Processor -> Arduino Devices
```

## File Descriptions

*   **`background_processor.py`**: The core application logic. This script contains the main processing loop, database interactions, API calls, and data standardization logic.
*   **`endpoint_configs.py`**: A configuration file that defines how to map data from different API endpoints to the standardized format. This allows for easy extension to support new APIs without modifying the core application logic.
*   **`requirements.txt`**: A list of Python dependencies required for the project.
*   **`test_background_processor.py`**: A test runner for the background processor. This script sets up a test environment and runs the main processing loop once to verify its functionality.
*   **`test_api.py`**: A script for testing the field extraction and standardization logic defined in `endpoint_configs.py`.
*   **`lamp_processor.log`**: The log file where all operational messages are written.
*   **`background_processor_backup.py`**: A backup of a previous version of the background processor.

## Setup and Configuration

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Database Schema

The background processor requires a PostgreSQL database with the following tables:

```sql
-- Stores information about each lamp
CREATE TABLE lamps (
    lamp_id SERIAL PRIMARY KEY,
    user_id INTEGER,
    arduino_id INTEGER,
    arduino_ip VARCHAR(255),
    last_updated TIMESTAMP
);

-- Stores information about the users
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    location VARCHAR(255),
    preferred_output VARCHAR(50) -- e.g., 'meters' or 'feet'
);

-- Stores information about the API usage
CREATE TABLE usage_lamps (
    usage_id INTEGER,
    lamp_id INTEGER,
    api_key VARCHAR(255),
    http_endpoint VARCHAR(255)
);

-- Stores information about the daily usage of websites
CREATE TABLE daily_usage (
    usage_id SERIAL PRIMARY KEY,
    website_url VARCHAR(255)
);
```

### 3. Environment Variables

The following environment variable must be set:

*   `DATABASE_URL`: The connection string for your PostgreSQL database.

Example:

```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
```

## Running the Background Processor

To run the background processor in continuous mode, execute the following command:

```bash
python background_processor.py
```

The processor will run once immediately and then every 30 minutes thereafter.

To run the processor in test mode (runs once and exits), set the `TEST_MODE` environment variable to `true`:

```bash
export TEST_MODE=true
python background_processor.py
```

## Running the Tests

To run the test suite, execute the following command:

```bash
python test_background_processor.py
```

This will run the main processing loop once and report on its success or failure.

## Arduino Endpoint

The background processor expects the Arduino devices to expose an HTTP endpoint at `/api/update`. The processor will send a POST request to this endpoint with a JSON payload containing the standardized surf data.

**Example Payload:**

```json
{
  "wave_height_m": 1.8,
  "wave_period_s": 9.2,
  "wind_speed_mps": 8.5,
  "wind_direction_deg": 225,
  "location": "San Diego",
  "timestamp": 1704067200
}
```

The Arduino should respond with a `200 OK` status and a JSON body of `{"status": "ok"}` to indicate success.

## Extending the System

To add support for a new API, you need to:

1.  Add a new entry to the `FIELD_MAPPINGS` dictionary in `endpoint_configs.py`. This entry should define how to extract the required data fields from the API's JSON response.
2.  Add the new API endpoint to the `daily_usage` and `usage_lamps` tables in the database.

The background processor will automatically detect the new configuration and start fetching data from the new API.
