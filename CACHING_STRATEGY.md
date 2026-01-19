# Surf Lamp Caching Strategy

## Data Flow Architecture

### CACHED DATA

| Data | Duration | Scope | Endpoint | Purpose |
|------|----------|-------|----------|---------|
| **Sunset calculations** | 24 hours | Per location | V1, Location endpoint | Avoid repeated astronomical calculations |
| **User coordinates** | 1 hour | Per user | V2 endpoint | Skip lat/lon lookups for same user |
| **Location conditions** | 5 minutes | Per location | CDN | Public conditions shared across lamps |

### NOT CACHED (Real-time)

| Data | Reason | Endpoint |
|------|--------|----------|
| User off/quiet hours | User-specific, time-sensitive | V1, V2 |
| User thresholds | User-specific preference | V1, V2 |
| User settings (theme, brightness) | User-specific preference | V1, V2, Settings |
| Arduino poll timestamps | Activity tracking | Database update |
| Wave/wind/period data | Changes every 15 minutes | Location conditions |

### CDN (Content Delivery Network)

**Status**: Headers configured, awaiting Cloudflare deployment

| Endpoint | Cache Duration | Content | Notes |
|----------|----------------|---------|-------|
| `/api/locations/{location}/conditions` | 5 minutes | Wave height, wind, sunset trigger | Shared by all lamps at location |
| Static assets | Long-lived | JS, CSS, images | Browser caching |

**Impact at scale**: CDN can reduce server load by 75% at 1500+ lamps

### SERVER-SIDE DATA (Database queries on every request)

| Data | Endpoint | Why |
|------|----------|-----|
| User-specific settings | V1, V2 | Must be fresh, user-specific |
| Off/Quiet hour logic | V1, V2 | Time-dependent, per user |
| Location lookup | All endpoints | Fast primary key lookup |
| Arduino metadata | All endpoints | Polling activity tracking |

---

## Endpoint Breakdown

### V1 `/api/arduino/<id>/data`
**Caching:**
- ✅ Sunset info (24h) - cached after first request per location
- ❌ User settings (fresh every request)
- ❌ Timezone/DST calculations
- ❌ Off/quiet hours logic

**Performance**: Best for single lamp, degrades under load

### V2 `/api/arduino/v2/<id>/data`
**Caching:**
- ✅ User coordinates (1h) - eliminated database lookups
- ✅ Timezone (static per location, part of coord cache)
- ❌ User settings (fresh every request)
- ❌ Off/quiet hours logic

**Performance**: Recommended for scale, Arduino calculates sunset locally

### Location Conditions `/api/locations/{location}/conditions`
**Caching:**
- ✅ Sunset info (24h) - cached after first request
- ✅ CDN-ready (5min cache headers)
- ❌ Condition data (sourced from location table, updated every 15 min)

**Performance**: Optimized for CDN, shared across all lamps at location

### Settings `/api/arduino/<id>/settings`
**Caching:**
- ✅ CDN-ready (1h cache headers)
- ❌ User preferences (always fresh)

**Performance**: Separate from conditions to enable selective caching

---

## Cache Invalidation

| Cache | Invalidated When | Mechanism |
|-------|------------------|-----------|
| Sunset (24h) | 24 hours elapsed | Time-based expiration |
| Coordinates (1h) | Location changed OR 1h elapsed | User change triggers invalidation |
| CDN (5min) | 5 minutes elapsed | Cache-Control header |

---

## Current Bottlenecks (Post-Optimization)

| Bottleneck | Status | Fix Applied |
|------------|--------|-------------|
| Single Gunicorn worker | ✅ Fixed | 2 workers configured |
| Repeated sunset calculations | ✅ Fixed | 24h caching |
| Repeated coordinate lookups | ✅ Fixed | 1h caching per user |
| CDN deployment | ⏳ Pending | Headers ready, Cloudflare needed |

---

## Scaling Path

**Current** (7 users, 7 Arduinos):
- All endpoints work fine without optimization

**1000 lamps (mostly V2)**:
- 2 Gunicorn workers → handle parallel requests
- Sunset cache → 95% hit rate
- Coordinate cache → 95% hit rate
- CDN not critical yet

**5000+ lamps**:
- Deploy CDN (Cloudflare)
- Reduce V1 endpoints (migrate to V2)
- Consider Redis for distributed caching

---

## How to Deploy CDN

```
1. Register Cloudflare account
2. Add domain to Cloudflare
3. Update DNS nameservers
4. Create cache rule for /api/locations/* (5 min)
5. Enable automatic cache purge on database updates
```

Estimated impact: **75% reduction in origin requests**
