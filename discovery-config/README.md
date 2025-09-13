# Discovery Configuration

This directory contains the server discovery configuration used by the Surf Lamp Arduino firmware.

## Overview

The Arduino firmware uses dynamic server discovery to avoid hardcoding server URLs. Instead of relying on a fixed backend server address, the firmware fetches this configuration file from GitHub Pages to determine the current API server location.

## Files

### `config.json`

The main configuration file that tells Arduino devices where to find the backend API server.

**Structure:**
```json
{
  "api_server": "final-surf-lamp.onrender.com",
  "backup_servers": [
    "backup-api.herokuapp.com", 
    "api.surflamp.com"
  ],
  "version": "1.0",
  "timestamp": 1692847200,
  "endpoints": {
    "arduino_data": "/api/arduino/{arduino_id}/data",
    "status": "/api/arduino/status"
  },
  "update_interval_hours": 24,
  "signature": "unsigned_for_now"
}
```

**Fields:**
- `api_server`: Primary server hostname for API requests
- `backup_servers`: Alternative servers (future use)
- `version`: Configuration version
- `timestamp`: Last update timestamp
- `endpoints`: API endpoint paths
- `update_interval_hours`: How often devices should check for updates
- `signature`: Digital signature (placeholder for future security)

## How It Works

1. **Arduino Startup**: When the Arduino boots up, it attempts to connect to the stored WiFi network
2. **Discovery Process**: Every 24 hours (or on first run), the device fetches this config from:
   - `https://shahar42.github.io/final_surf_lamp/discovery-config/config.json`
   - `https://raw.githubusercontent.com/shahar42/final_surf_lamp/master/discovery-config/config.json`
3. **Server Selection**: The device uses the `api_server` value to make all subsequent API calls
4. **Fallback**: If discovery fails, devices fall back to hardcoded servers in `ServerDiscovery.h`

## Updating the Configuration

To change the backend server:

1. **Update config.json**: Modify the `api_server` field with the new server hostname
2. **Update timestamp**: Set to current Unix timestamp
3. **Commit and push**: Changes will be automatically available via GitHub Pages
4. **Wait for propagation**: Arduino devices will pick up changes within 24 hours

## Benefits

- **Zero-downtime server migration**: Update config file to point to new servers
- **No firmware updates required**: Server changes don't require reflashing devices
- **Redundancy**: Multiple discovery URLs and fallback servers
- **Version control**: All server changes are tracked in git history

## Security Considerations

- Configuration is served over HTTPS from GitHub
- Currently unsigned (signature field is placeholder)
- Future versions may include cryptographic signatures for integrity verification

## Deployment

This directory should be published to GitHub Pages at:
`https://shahar42.github.io/final_surf_lamp/discovery-config/`

The Arduino firmware expects the config to be accessible at that exact path.