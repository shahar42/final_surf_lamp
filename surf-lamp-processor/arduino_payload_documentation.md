# Arduino API & Payload Documentation

This document details the API endpoint the Arduino device uses to fetch surf data from the web server. The system uses a **PULL model**, where the device is responsible for periodically requesting updates.

## API Versioning

*   **Current Version:** `2.0`
*   **Description:** This version uses a `GET` request from the device to the server, replacing the legacy push model. This improves device autonomy and simplifies the backend.

## Primary Data Endpoint

The device fetches all its required data from a single, dynamic endpoint.

*   **Method:** `GET`
*   **URL Structure:** `/api/arduino/<arduino_id>/data`
*   **Parameters:**
    *   `arduino_id` (integer): The unique ID of the lamp making the request. This is required.

---

### ✅ Success Response (200 OK)

When data is available for the requested `arduino_id`, the server responds with a JSON object containing the latest surf conditions and user preferences.

#### Example Payload (Data Available)

```json
{
  "wave_height_cm": 125,
  "wave_period_s": 8.5,
  "wind_speed_mps": 5,
  "wind_direction_deg": 270,
  "wave_threshold_cm": 100,
  "wind_speed_threshold_knots": 15,
  "led_theme": "day",
  "last_updated": "2025-09-15T14:30:00Z",
  "data_available": true
}
```

#### Field Descriptions

| Field                        | Type    | Unit         | Description                                                                 |
| ---------------------------- | ------- | ------------ | --------------------------------------------------------------------------- |
| `wave_height_cm`             | Integer | Centimeters  | The significant wave height, converted to an integer.                       |
| `wave_period_s`              | Float   | Seconds      | The dominant wave period.                                                   |
| `wind_speed_mps`             | Integer | Meters/Second| The wind speed, rounded to the nearest integer.                             |
| `wind_direction_deg`         | Integer | Degrees      | The wind direction in meteorological degrees (0° = North, 90° = East).      |
| `wave_threshold_cm`          | Integer | Centimeters  | The user's configured wave height threshold for triggering a blinking alert. |
| `wind_speed_threshold_knots` | Integer | Knots        | The user's configured wind speed threshold for triggering a blinking alert.  |
| `led_theme`                  | String  | -            | The user's preferred color theme (`"day"` or `"night"`).                     |
| `last_updated`               | String  | ISO 8601     | The timestamp when the data was last updated on the server.                 |
| `data_available`             | Boolean | -            | `true` if fresh data is available; `false` otherwise.                       |

---

### ℹ️ Success Response (No Data Available)

If the server has not yet processed data for the lamp (e.g., on first boot), it will still return a `200 OK` status but with default values and `"data_available": false`. The device should handle this gracefully.

#### Example Payload (No Data)

```json
{
  "wave_height_cm": 0,
  "wave_period_s": 0.0,
  "wind_speed_mps": 0,
  "wind_direction_deg": 0,
  "wave_threshold_cm": 100,
  "wind_speed_threshold_knots": 22,
  "led_theme": "day",
  "last_updated": "1970-01-01T00:00:00Z",
  "data_available": false
}
```

---

### ❌ Error Response (404 Not Found)

If the `arduino_id` sent by the device does not exist in the database, the server will respond with a `404 Not Found` error.

#### Example Error Payload

```json
{
  "error": "Arduino not found"
}
```

**Device Handling:** Upon receiving a 404, the device should assume it is not properly registered and should probably cease trying to fetch data until it is rebooted or reconfigured.

## 🧪 Testing with `curl`

You can test the API endpoint from the command line using `curl`. Replace `<your_server_address>` and `<your_arduino_id>` with the actual values.

#### Test a valid Arduino ID:

```bash
curl -X GET http://<your_server_address>/api/arduino/<your_arduino_id>/data
```

#### Test an invalid Arduino ID:

```bash
# This should return a 404 error
curl -i -X GET http://<your_server_address>/api/arduino/999999/data
```