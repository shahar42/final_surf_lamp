# SUPER IMPORTANT FINDINGS 🚨

## 1. The "Ghost Lamp" Mystery (Arduino 5)
We observed that **Arduino 5** (User: Raznitzan) appeared to be "active" and pulling data, even though the physical lamp is powered off.

**The Cause:** 
The requests are coming from a **Web Browser Dashboard**, not physical hardware.
- **Evidence:** Render logs show the `Referer` header as `https://final-surf-lamp-web.onrender.com/dashboard`.
- **Impact:** The Live LED Visualization on the website uses the exact same API endpoint as the physical ESP32. If a user leaves their dashboard open, the server thinks the lamp is "Online."

## 2. Processor "Fake Activity" Logic
During the schema refactor, we discovered a logic flaw in how the system tracks "Online" status.

**The Issue:**
In `surf-lamp-processor/background_processor.py`, the code does this:
```python
# Update location table ONCE
update_location_conditions(engine, location, combined_surf_data)

# Update arduino timestamps to track polling activity
arduino_ids = [arduino['arduino_id'] for arduino in arduinos]
batch_update_arduino_timestamps(engine, arduino_ids)
```
- **The Bug:** The processor marks **EVERY** lamp in a location as "updated" just because it fetched new data for that location.
- **The Reality:** This only means the *database* has new data for them, NOT that the *physical lamp* actually checked in.

## 3. Monitoring Tool Pollution
Because of the two points above, our monitoring tools (like `get_lamp_status_summary`) are currently unreliable for checking physical hardware health:
1. **Dashboards** create "User Activity" that looks like "Lamp Activity."
2. **Processor** creates "Database Updates" that look like "Lamp Heartbeats."

## Recommended Fixes
1. **Differentiate User vs Lamp:** Add a `User-Agent` check or a separate endpoint for the Dashboard visualization so it doesn't trigger the `last_poll_time`.
2. **Remove Batch Updates:** The `background_processor` should **NEVER** update `last_poll_time`. Only the `/api/arduino/<id>/data` endpoint (called by the actual device) should update that timestamp.
3. **True Heartbeat:** Use the `last_poll_time` ONLY for actual hardware check-ins to get a real count of how many physical lamps are currently plugged in.
