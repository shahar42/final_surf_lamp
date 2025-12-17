# Maayan's Lamp Configuration

## Surf Data Scaling
- Max wave height: 3 meters
- Max wind speed: 35 knots
- Wave period: 1 LED = 1 second

## LED Strip Mapping
- Right strip (wave height): bottom LED 5 → top LED 27 (23 LEDs, FORWARD)
- Middle strip (wind speed): bottom LED 58 → top LED 34 (25 LEDs, REVERSE)
- Left strip (wave period): bottom LED 65 → top LED 86 (22 LEDs, FORWARD)

## WiFi Configuration
- **Retry attempts:** 10 (covers router boot time ~2-4 minutes)
- **Timeout per attempt:** 30 seconds
- **Total retry time:** ~5 minutes before AP mode
- **Location fingerprinting:** Enabled (auto-detects new location)

