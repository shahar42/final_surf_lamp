# Surf Lamp - Shipping Preparation Guide

## Overview

This document outlines the changes needed to prepare the Surf Lamp firmware for shipping to customers. The current firmware already has a complete dynamic WiFi configuration system implemented, but contains hardcoded WiFi credentials that need to be removed before shipping.

## Current WiFi Configuration System

The firmware already includes:
- ✅ **Automatic Configuration Portal** - Creates "SurfLamp-Setup" network when WiFi connection fails
- ✅ **Web-based Setup Interface** - User-friendly portal at http://192.168.4.1 for WiFi setup
- ✅ **Persistent Storage** - WiFi credentials saved to ESP32 NVRAM using Preferences library
- ✅ **Automatic Fallback** - Automatically enters config mode if stored WiFi fails
- ✅ **Timeout Protection** - AP mode timeout prevents device from staying in config mode indefinitely

## Changes Required for Shipping

### 1. Remove Hardcoded WiFi Credentials

**File:** `arduinomain_lamp.ino`
**Lines:** 48-49

**Current Code:**
```cpp
// Wi-Fi credentials (defaults)
char ssid[32] = "Sunrise";
char password[64] = "4085429360";
```

**Change To:**
```cpp
// Wi-Fi credentials (will be loaded from stored preferences or set via config portal)
char ssid[32] = "";
char password[64] = "";
```

**Impact:** 
- Device will have no default WiFi credentials
- On first boot, it will automatically enter configuration mode
- Customer will be guided through WiFi setup via the web portal

### 2. Verify Configuration Portal Settings

**Current Settings (No Changes Needed):**
- **SSID:** `SurfLamp-Setup` 
- **Password:** `surf123456`
- **Portal URL:** `http://192.168.4.1`
- **Timeout:** 60 seconds before retrying WiFi connection

These settings are appropriate for shipping and provide good security.

### 3. Update Device ID for Each Unit

**File:** `arduinomain_lamp.ino`
**Line:** 31

**Current Code:**
```cpp
const int ARDUINO_ID = 4433;  // ✨ CHANGE THIS for each Arduino device
```

**Action Required:**
- Set unique ARDUINO_ID for each device before flashing
- This ID must match the registration in the web dashboard
- Consider using a systematic numbering scheme (e.g., 1001, 1002, 1003...)

## Shipping Process

### Pre-Shipping Checklist

1. **Firmware Preparation:**
   - [ ] Remove hardcoded WiFi credentials (change lines 48-49)
   - [ ] Set unique ARDUINO_ID for the device
   - [ ] Flash firmware to ESP32
   - [ ] Test LED functionality

2. **WiFi Configuration Test:**
   - [ ] Power on device (should create "SurfLamp-Setup" network)
   - [ ] Connect to setup network with password "surf123456"
   - [ ] Navigate to http://192.168.4.1
   - [ ] Verify configuration portal loads correctly
   - [ ] Test WiFi connection with known network
   - [ ] Verify device connects and serves API endpoints

3. **Factory Reset (Optional):**
   - [ ] Clear any stored WiFi preferences if needed
   - [ ] Power cycle to ensure clean state

### Customer Setup Instructions

The customer setup process will be:

1. **Power On Device** - Device will create "SurfLamp-Setup" WiFi network
2. **Connect to Setup Network** - Password: "surf123456"
3. **Open Configuration Portal** - Automatic captive portal or http://192.168.4.1
4. **Enter WiFi Credentials** - Input their home WiFi SSID and password
5. **Device Connects** - Automatic connection to their network
6. **Registration** - Device becomes available at local IP for dashboard registration

## Additional Considerations

### Security
- The setup password "surf123456" provides basic security during configuration
- Consider if this password should be changed or made device-specific

### Documentation
- Update README.md if needed to reflect shipping configuration
- Ensure customer documentation includes setup instructions
- Consider creating setup instruction cards/QR codes for customers

### Testing
- Test the complete customer setup flow before shipping
- Verify server discovery works correctly after WiFi configuration
- Ensure LED test functionality works for customer verification

## Emergency Fallback

If a customer has issues with WiFi configuration:
- Device will retry connection every 30 seconds
- After extended failures, it will re-enter configuration mode
- Button on GPIO pin 0 can be used for manual reset if needed

## File Summary

**Files to Modify:**
- `arduinomain_lamp.ino` (lines 31, 48-49)

**Files to Review:**
- `README.md` (update setup instructions if needed)

**Files Unchanged:**
- `ServerDiscovery.h` (dynamic server discovery already implemented)
- All other functionality remains the same