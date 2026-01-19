# Maayan's Lamp Configuration Card

**Device Name:** Maayan's Lamp
**Arduino ID:** 6
**Owner:** Maayan
**Model:** V2 Custom
**Hardware:** ESP32 NodeMCU

## LED Strip Mapping (WS2812B / GPIO 2)

| Strip | Start LED | End LED | Count | Direction | Function |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Right** | 3 | 16 | 14 | Forward | Wave Height (0-3.0m) |
| **Center** | 38 | 21 | 18 | Reverse | Wind Speed (0-35kts) |
| **Left** | 41 | 55 | 15 | Forward | Wave Period (s) |

**Total LEDs:** 56 (Indices 0-55)

### Special LEDs
*   **Status LED:** 38 (Bottom of Wind Strip)
*   **Wind Direction:** 21 (Top of Wind Strip)

### Notes
*   **Center Strip:** Wired in reverse (Top=Low Index, Bottom=High Index).
*   **Gap LEDs:** LEDs 0-2, 17-20, 39-40 are hidden/unused connectors.
