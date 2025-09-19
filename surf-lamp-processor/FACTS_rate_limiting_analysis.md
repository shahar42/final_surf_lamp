# FACTS: Open-Meteo Rate Limiting Analysis

## ✅ CONFIRMED FACTS

### Working APIs
- **Isramar APIs**: 100% success rate in recent logs
  - `https://isramar.ocean.org.il/isramar2009/station/data/Hadera_Hs_Per.json`
  - Returns: wave_height_m, wave_period_s, wave_direction_deg
  - Response time: ~30 seconds, Status: 200

### Failing APIs
- **Open-Meteo Wind APIs ONLY**: 100% failure rate (429 errors) in recent logs
  - `https://api.open-meteo.com/v1/forecast?latitude=X&longitude=Y&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms`
  - `https://api.open-meteo.com/v1/gfs?latitude=X&longitude=Y&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms`
  - Error: 429 Client Error: Too Many Requests

### Working Open-Meteo APIs (CRITICAL!)
- **marine-api.open-meteo.com**: 100% success rate
  - `https://marine-api.open-meteo.com/v1/marine?latitude=31.7939&longitude=34.6328&hourly=wave_height,wave_period,wave_direction`
  - Response time: ~30 seconds, Status: 200
  - Returns: wave_height_m (0.98), wave_period_s (6.85), wave_direction_deg (297)

### Historical Performance
- **August 15, 2025**: Open-Meteo APIs worked perfectly
  - Log evidence: `✅ API call successful: 200`
  - Same endpoints, same request pattern
  - No authentication used then either

### Current System Behavior
- **Location-based processing**: Working correctly (6 API calls for 7 lamps vs 21 if lamp-by-lamp)
- **Database updates**: All 7 lamps updated successfully with available data
- **Processing time**: 636 seconds (10+ minutes) due to retry delays
- **Wave data**: Complete and accurate from Isramar
- **Wind data**: Missing due to Open-Meteo failures

### Authentication Status
- **Open-Meteo**: No API key used ("Making API request without authentication")
- **Isramar**: No API key used (public endpoint, works fine)

### Rate Limiting Behavior
- **First attempt**: Immediate 429 error
- **Retry pattern**: 60s + 120s exponential backoff
- **All retries fail**: After 180 seconds per endpoint
- **No successful calls**: Zero Open-Meteo requests succeed

### Request Parameters
- **Headers**: `{'User-Agent': 'SurfLamp-Agent/1.0'}`
- **Timeout**: 15 seconds
- **Delay between calls**: 30 seconds
- **Endpoints include**: Required `&wind_speed_unit=ms` parameter

### Deployment Pattern (CRITICAL FACT)
- **Fresh Render deployment**: Open-Meteo APIs work initially
- **After a few hours**: Open-Meteo APIs start failing with 429 errors
- **Pattern repeats**: Every new deployment → works → fails after hours

## 🔍 OBSERVATIONS (Not Facts)

### Timeline Questions
- ~~When exactly did Open-Meteo start failing?~~ **ANSWERED: After few hours of each deployment**
- What changed between August 15 and now?
- ~~Is this a gradual degradation or sudden failure?~~ **ANSWERED: Gradual degradation within hours**

### Rate Limit Facts (CONFIRMED)
- **Open-Meteo Free Limits** (same for authenticated/anonymous):
  - 600 calls/minute
  - 5,000 calls/hour
  - 10,000 calls/day
  - 300,000 calls/month
- **Only paid commercial plans** get higher limits with API keys
- **Free API keys do NOT increase limits** over anonymous usage

### ROOT CAUSE IDENTIFIED ✅
**Open-Meteo uses SEPARATE infrastructure and rate limit pools for different services:**

**Important:** Subdomains don't "crash" - they actively return 429 responses when rate limits are exceeded. This is standard API behavior, not a service outage.

- **marine-api.open-meteo.com** = Marine API (separate quota pool)
- **api.open-meteo.com** = Weather API (separate quota pool)
- **Independent rate limiting** - throttling one doesn't affect the other
- **Marine API likely has less traffic** or more generous limits due to niche use
- **Weather API heavily used** - shared quota limits actively enforced via 429 responses

**This explains the behavior:**
- Marine API works fine (its quota pool under limits)
- Weather API returns 429 immediately (rate limiting actively blocking requests)
- Fresh deployments work initially (new IP gets brief quota before hitting shared limits)

## 🎯 SOLUTION OPTIONS

### Option 1: Alternative Wind APIs (RECOMMENDED)
- **NOAA/Weather.gov** - US government weather service
- **WeatherAPI.com** - free tier with higher limits
- **OpenWeatherMap** - established service with clear rate limits
- **Local meteorological services** - Israeli weather services

### Option 2: Commercial Open-Meteo Plan
- **Pros**: Keep existing architecture, dedicated quota pools
- **Cons**: Monthly cost, requires business justification

### Option 3: Optimize Current Usage
- **Cache wind data longer** (2-4 hours instead of 20 minutes)
- **Reduce call frequency** during peak hours
- **Smart retry logic** with exponential backoff across hours

### Option 4: Hybrid Approach
- **Keep marine-api.open-meteo.com** for wave data (working perfectly)
- **Replace api.open-meteo.com** with alternative wind service
- **Maintain current location-based processing architecture**

## 📊 IMPACT ANALYSIS

**Current Status:**
- ✅ **System functional** - all 7 lamps updating successfully
- ✅ **Wave data complete** - Isramar + marine-api working
- ❌ **Wind data missing** - essential for complete surf forecast
- ⏱️ **Processing time excessive** - 636 seconds due to retry delays

**Priority:** **High** - Wind data is essential for surf conditions

---
*Created: 2025-09-19*
*Updated: 2025-09-19*
*Status: ROOT CAUSE IDENTIFIED - Ready for solution implementation*
*Recommendation: Implement Option 4 (Hybrid Approach) for fastest resolution*