# Lamp Configuration Files

**Purpose:** Store configuration documentation for individual surf lamps.

Each file documents the specific LED mappings and parameters for a physical lamp.

---

## Files

- `lamp_7_config.md` - Configuration for Lamp 7
- `lamp_8_config.md` - Configuration for Lamp 8

---

## Format

Each config file should document:

1. **Arduino ID** - Unique lamp identifier
2. **Total LEDs** - Physical LED count on the strip
3. **LED Strip Mapping:**
   - Wave Height Strip (bottom/top indices)
   - Wave Period Strip (bottom/top indices)
   - Wind Speed Strip (bottom/top indices)
4. **Scaling Parameters:**
   - Max wave height (meters)
   - Max wind speed (m/s or knots)
5. **Notes:** Any special configuration or hardware details

---

## Usage

These config files serve as:
- Quick reference when configuring new lamps
- Documentation of existing lamp setups
- Troubleshooting reference for LED mapping issues
- Template for creating new lamp configs

To configure a new lamp based on these, copy the Config.h template and use the values from the appropriate config file.

---

## Related Tools

- **Marker Calculator:** See `../Legends_marking/` for LED position marking tool
- **Config Template:** See `../lamp_template/Config.h` for the actual configuration file

---

**Note:** These are documentation files, not code. The actual lamp configuration is in each lamp's `Config.h` file.
