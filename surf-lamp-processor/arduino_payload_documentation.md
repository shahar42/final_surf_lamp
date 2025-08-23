# Arduino Payload Documentation

The Surf Lamp processor will send data to the Arduino via an HTTP POST request to the `/api/update` endpoint on the IP address configured for it in the database.

The request body will contain a JSON object with the following structure and fields.

## Sample JSON Payload

```json
{
  "wave_period_s": 5.9,
  "wind_direction_deg": 180,
  "wind_speed_mps": 3,
  "local_time": "2025-08-24 01:30:29 IDT",
  "timezone": "Asia/Jerusalem",
  "wave_height_cm": 55,
  "wave_threshold_cm": 100
}
```

## Field Descriptions

| Field                 | Type    | Description                                                                                             | Example Value        |
| --------------------- | ------- | ------------------------------------------------------------------------------------------------------- | -------------------- |
| `wave_height_cm`      | Integer | The significant wave height, converted to centimeters.                                                  | `55`                 |
| `wave_period_s`       | Float   | The dominant wave period in seconds.                                                                    | `5.9`                |
| `wind_speed_mps`      | Integer | The wind speed in meters per second, rounded to the nearest integer.                                    | `3`                  |
| `wind_direction_deg`  | Integer | The direction the wind is coming from, in degrees (0-360).                                              | `180` (South)        |
| `wave_threshold_cm`   | Integer | The user-defined wave height threshold, in centimeters. The lamp should light up if `wave_height_cm` exceeds this value. | `100`                |
| `local_time`          | String  | The current time at the lamp's location, formatted as a string. Includes timezone abbreviation.         | `"2025-08-24 01:30:29 IDT"` |
| `timezone`            | String  | The IANA timezone name for the lamp's location.                                                         | `"Asia/Jerusalem"`   |

### Notes for Arduino Developer:

*   All fields should be present in every request. If a value could not be fetched from an API (e.g., wind data was unavailable), it will be sent with a default value of `0` or `0.0`.
*   The Arduino should parse the incoming JSON to extract these values to control the lamp's display.
*   The most critical fields for the lamp's core logic are `wave_height_cm` and `wave_threshold_cm`.
