# ServerDiscovery - Technical Documentation

## 1. Overview

**What it does**: GitHub Pages-hosted JSON file that enables zero-downtime server migrations by allowing Arduino lamps to dynamically discover the current production API server address without firmware reflashing.

**Why it exists**: Decouples device firmware from infrastructure deployment URLs - when backend moves to new domain, update single JSON file instead of reflashing hundreds of deployed devices.

## 2. Technical Details

### What Would Break If This Disappeared?

- **Immediate**: Arduinos fall back to hardcoded `fallback_servers[0]` in firmware (currently `final-surf-lamp.onrender.com`)
- **Long-term**: Server migrations require physical device access for reflashing - deployment flexibility destroyed
- **Fleet Management**: No centralized control over which backend URL devices contact

### Critical Assumptions

- GitHub Pages remains accessible (99.9% uptime SLA)
- JSON format never changes (`api_server` key sacred)
- 24-hour cache window acceptable for migrations (gradual rollout)
- No authentication required (public read access)
- DNS resolution for `shahar42.github.io` works globally

### Where Complexity Hides

**Edge Cases**:
- **Partial Fleet Updates**: During migration window, some devices on old server, some on new (24h stagger)
- **GitHub Outage**: All new boots fall back to hardcoded servers - creates thundering herd if fallback dead
- **Invalid JSON**: Parse failure silently uses last known good server (cached in Arduino memory)
- **DNS Poisoning**: No signature verification - MITM could redirect entire fleet

**Race Conditions**:
- Arduino checks cache expiry at boot + every 24h - if GitHub slow to respond, may timeout and keep stale cache
- Git push to GitHub Pages has 1-5 minute deployment delay - immediate git push doesn't mean immediate availability

### Stories the Code Tells

**Git History**: Only one commit touching discovery (`39b5faf "Fix Arduino server discovery URL"`) - suggests system deployed correctly first try or URLs infrequently change

**Design Philosophy**: Extreme simplicity over security - no signatures, no encryption, no versioning logic (just timestamp for humans)

## 3. Architecture & Implementation

### Data Flow

```
[Git Push to GitHub] → [GitHub Pages Deploy (1-5 min)] → [JSON Available at shahar42.github.io]
                                                                     ↓
[Arduino Boot or 24h Timer] → [HTTP GET config.json] → [Parse api_server field]
                                      ↓ (if fails)
                           [Use Hardcoded Fallback Servers]
```

### Configuration Format

**Required File**: `surflamp-discovery/config.json`

```json
{
  "api_server": "final-surf-lamp-web.onrender.com",
  "version": "1.1",
  "timestamp": 1727434800
}
```

**Field Contracts**:
- `api_server` (required): Domain without protocol (Arduino prepends `https://`)
- `version` (optional): Human-readable config version
- `timestamp` (optional): Unix timestamp for tracking updates

**Arduino Fetch URLs** (tried in sequence):
1. `https://shahar42.github.io/final_surf_lamp/discovery-config/config.json`
2. `https://raw.githubusercontent.com/shahar42/final_surf_lamp/master/discovery-config/config.json`

### Key Implementation Details

**ServerDiscovery.h Logic**:
- Cache expiry: `DISCOVERY_INTERVAL = 24 * 60 * 60 * 1000` (24 hours)
- Timeout per URL: 10 seconds
- Retry delay between URLs: 1 second
- Validation: `server.indexOf('.') > 0 && server.length() > 5` (basic sanity check)

## 4. Integration Points

### What Calls This Component

- **Arduino Firmware**: `serverDiscovery.getApiServer()` called before every surf data fetch (13-min intervals)
- **Git Workflow**: Developers push to GitHub when deploying new backend

### What This Component Calls

- **GitHub Pages**: Serves static JSON (no backend processing)
- **Nothing else**: Pure static file hosting

### Data Contracts

**GitHub Pages → Arduino**:
```json
{
  "api_server": "domain.com"  // String, no protocol prefix
}
```

Arduino strips `http://` and `https://` if present, validates format, caches for 24h.

## 5. Troubleshooting & Failure Modes

### Common Issues

**Problem: Devices Not Picking Up New Server**
- **Detection**: Check Arduino serial logs: "⚠️ Discovery failed, using current: old-server.onrender.com"
- **Causes**: JSON syntax error, GitHub Pages deploy delay, DNS issues
- **Recovery**:
  1. Verify JSON valid: `curl https://shahar42.github.io/final_surf_lamp/discovery-config/config.json | jq`
  2. Wait 5 minutes for GitHub Pages deployment
  3. Check GitHub Pages settings enabled
  4. Devices auto-recover on next 24h check

**Problem: GitHub Pages 404**
- **Detection**: `curl` returns 404, Arduino logs show HTTP errors
- **Causes**: Repo renamed, GitHub Pages disabled, wrong branch selected
- **Recovery**: Re-enable GitHub Pages in repo Settings → Pages → Deploy from branch

**Problem: Fleet Split Across Two Servers**
- **Detection**: Database shows lamps with stale data on old server
- **Expected Behavior**: 24-hour gradual migration by design
- **Mitigation**: Plan migrations during low-traffic windows, monitor both servers for 48h

### Scaling Concerns

**GitHub Pages Bandwidth**:
- Current: ~7 requests/min for 10k devices (1 fetch per device per 24h)
- Limit: 100 GB/month soft quota
- JSON size: ~80 bytes × 7 req/min × 60 min × 24 h × 30 days = ~3 MB/month
- **No concern at any realistic scale**

**DNS Cache Poisoning**:
- No signature verification - malicious GitHub Pages could hijack fleet
- Mitigation: Move to signed JWTs or HTTPS cert pinning in future

---

*Last Updated: 2025-09-30*
*Hosted at: https://shahar42.github.io/final_surf_lamp/discovery-config/config.json*