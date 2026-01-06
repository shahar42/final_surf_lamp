# Plan: Range Alert Feature (Server-Side Logic Shim)

## Goal
Implement a "range alert" feature (e.g., blink only if wave height is between 1m and 3m) without modifying the Arduino firmware.

## Strategy: "Server-Side Logic Shim" / "Dynamic Threshold Injection"
The Arduino logic is fixed: `if (current_value >= threshold) blink()`.
We will dynamically manipulate the `threshold` value sent to the Arduino based on the user's defined range `[min, max]`.

### Logic
For a user-defined range `[min, max]`:
1.  **Condition:** `min <= current_value <= max` (Alert SHOULD be active)
    *   **Action:** Send `threshold = min`
    *   **Arduino Result:** `current >= min` → **True** (Blinks)
2.  **Condition:** `current_value < min` (Alert should be inactive - too low)
    *   **Action:** Send `threshold = min`
    *   **Arduino Result:** `current >= min` → **False** (No Blink)
3.  **Condition:** `current_value > max` (Alert should be inactive - too high)
    *   **Action:** Send `threshold = 9999` (or `current_value + 1`)
    *   **Arduino Result:** `current >= 9999` → **False** (No Blink)

## Implementation Steps

### 1. Database Schema Update
Add new columns to the `users` table to store the upper limits.
*   `wave_threshold_max_m` (Float, nullable, default NULL)
*   `wind_threshold_max_knots` (Float, nullable, default NULL)

*Migration Script:*
```sql
ALTER TABLE users ADD COLUMN wave_threshold_max_m FLOAT DEFAULT NULL;
ALTER TABLE users ADD COLUMN wind_threshold_max_knots FLOAT DEFAULT NULL;
```

### 2. Backend Logic Module (`web_and_database/utils/threshold_logic.py`)
Create a pure function to encapsulate this logic, making it easy to test and debug.

```python
def calculate_effective_threshold(current_value, user_min, user_max):
    """
    Calculates the threshold to send to the Arduino to simulate a range check.
    """
    # ... implementation of the logic above ...
```

### 3. API Integration (`web_and_database/blueprints/api_arduino.py`)
Update `get_arduino_surf_data` and `get_arduino_surf_data_v2`:
*   Import `calculate_effective_threshold`.
*   Retrieve `user.wave_threshold_max_m` and `user.wind_threshold_max_knots`.
*   Use the function to determine the `wave_threshold_cm` and `wind_speed_threshold_knots` values sent in the JSON response.

### 4. User API Update (`web_and_database/blueprints/api_user.py`)
Update endpoints to accept max values:
*   `POST /update-threshold`: Accept `min` and `max` (or `threshold_min`, `threshold_max`).
*   `POST /update-wind-threshold`: Accept `min` and `max`.

### 5. Frontend UI (`web_and_database/templates/dashboard.html` & JS)
*   Replace simple number inputs with a **Range Slider** (e.g., dual-handle slider) or two input fields ("Min" and "Max").
*   Update `web_and_database/static/js/features/wave-threshold.js` and `wind-threshold.js` to handle the new data structure.

## Verification
*   **Unit Tests:** Test `calculate_effective_threshold` with various edge cases (current < min, current in range, current > max, max is None).
*   **Integration Test:** Verify the API returns the "fake" high threshold when conditions exceed the max.
