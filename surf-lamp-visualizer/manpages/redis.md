# Redis Cache - Technical Documentation

## 1. Overview

**What it does**: In-memory key-value store providing rate limiting for Flask web application endpoints. Tracks request counts per IP address to prevent abuse of authentication endpoints (login, registration, password reset) and API endpoints using Flask-Limiter with fixed-window strategy.

**Why it exists**: Protects weather API quotas by limiting how frequently users can trigger backend operations. Prevents brute force attacks on authentication endpoints, DDoS attempts, and rapid-fire user preference changes that would overwhelm the background processor and external APIs.

## 2. Technical Details

### What Would Break If This Disappeared?

- **Rate Limiting Disabled**: Flask-Limiter falls back to in-memory storage (line 66-73 in app.py) - limits not enforced across multiple web server instances
- **Brute Force Protection Lost**: Login endpoint becomes vulnerable to password guessing attacks - 3/15min limit disappears (line 319)
- **Registration Spam**: Registration endpoint loses 10/minute protection - bot signups unrestricted (line 388)
- **Password Reset Abuse**: Forgot password endpoint loses 5/hour limit - email flooding possible (line 275)
- **Multi-Instance Rate Limits**: In multi-instance deployments on Render, each instance tracks separately - users can bypass limits by hitting different instances
- **Location Change Tracking**: Still works via in-memory dict but NOT stored in Redis (line 76 - architectural inconsistency)

### Critical Assumptions

**Redis Assumptions**:
- Redis instance accessible via `REDIS_URL` environment variable (line 63: `redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')`)
- Fallback to localhost:6379 for local development (line 63)
- Socket connection timeout 30 seconds (line 69: `storage_options={"socket_connect_timeout": 30}`)
- No authentication required (connection string format: `redis://hostname:port` not `redis://:password@hostname:port`)
- Redis persistence not required - rate limit counters ephemeral, reset on Redis restart acceptable
- Render Redis addon provides standard connection string in environment

**Flask-Limiter Assumptions**:
- Fixed-window strategy (line 70: `strategy="fixed-window"`)
- Key function uses client IP address (line 67: `key_func=get_remote_address`)
- Reverse proxy headers trusted due to ProxyFix middleware (app.py line 52: `app.wsgi_app = ProxyFix(app.wsgi_app)`)
- Rate limit decorators applied to routes before request processing (line 275, 319, 388, 447, 593)
- Limits enforced before route handler executes - blocked requests return 429 status

**Application Integration Assumptions**:
- `REDIS_URL` provided by Render Redis addon in production
- Web application running behind reverse proxy (Render's infrastructure)
- `X-Forwarded-For` header contains real client IP (line 67 relies on this via ProxyFix)
- Rate limit storage separate from application data (Redis used only for counters, not business logic)

### Where Complexity Hides

**Edge Cases**:

1. **Redis Connection Failure** (line 66-73):
   - Flask-Limiter initialization with `storage_uri` but no explicit failure handling
   - If Redis unavailable at startup, limiter falls back to in-memory storage silently
   - No logging of fallback mode - operators unaware rate limits ineffective across instances
   - 30-second connection timeout (line 69) means slow Redis causes 30s startup delay

2. **Location Change Rate Limiting NOT in Redis** (line 76, line 200-220):
   - `location_changes = {}` dict stored in-memory, not Redis
   - Architectural inconsistency: Flask-Limiter uses Redis, custom location limit doesn't
   - Multi-instance deployment: Each instance has separate `location_changes` dict
   - User can bypass 7/day limit by hitting different Render instances
   - Memory leak potential: Dict grows unbounded as users never removed (only timestamps pruned)

3. **Fixed-Window Rate Limit Boundary** (line 70):
   - Strategy allows burst at window boundaries
   - Example: 10/minute limit allows 10 requests at 00:59, 10 more at 01:00 = 20 in 1 second
   - Attacker can time requests to exploit window edges
   - Alternative sliding-window strategy would smooth this but increases Redis operations

4. **IP-Based Rate Limiting** (line 67):
   - Key function `get_remote_address` trusts `X-Forwarded-For` header via ProxyFix
   - NAT/corporate networks: Multiple users share IP, legitimate users blocked by one abuser
   - VPN users: Changing VPN server bypasses IP-based limits
   - IPv6: Multiple addresses per user if dual-stack, potentially bypassing limits

5. **Decorator Application Order**:
   - `@limiter.limit()` must be applied AFTER route decorator (line 275, 319, etc.)
   - If order reversed, rate limiting not enforced
   - No runtime validation of decorator order - fails silently

**Race Conditions**:

1. **Location Change Dict Concurrent Access** (line 200-220):
   - `check_location_change_limit()` reads, modifies, writes `location_changes` dict
   - Not thread-safe - concurrent requests from same user could corrupt list
   - Flask development server single-threaded, but production gunicorn multi-worker
   - Could result in: Missing timestamps, duplicate timestamps, incorrect count

2. **Redis Connection Pool Exhaustion**:
   - Flask-Limiter creates connection pool to Redis (default size not specified)
   - High request volume could exhaust connections
   - Blocked requests wait for connection, causing cascading delays
   - No explicit pool size configuration in code (line 66-73)

**Rate Limiting Concerns**:

1. **Endpoint-Specific Limits** (app.py):
   - Forgot password: `5 per hour` (line 275) - prevents email flooding
   - Login: `3 per 15 minutes` (line 319) - prevents brute force, maybe too strict for legitimate users
   - Registration: `10/minute` (line 388) - prevents bot signups
   - Dashboard routes: `10/minute` (line 447, 593) - prevents dashboard spam
   - Location changes: Custom `7 per day` via in-memory dict (line 215) - NOT Redis

2. **No Rate Limit on Arduino Endpoints**:
   - `/api/arduino/{id}/data` has no rate limit decorator
   - Compromised Arduino could DDoS by polling every second instead of 13 minutes
   - Trust-based security - assumes Arduinos behave correctly
   - Could add limit like `@limiter.limit("10/minute")` but legitimate polling is ~1/13min = 0.077/min

3. **Rate Limit Headers Not Exposed**:
   - Flask-Limiter can add `X-RateLimit-*` headers to responses
   - Not configured in code (line 66-73)
   - Clients can't see remaining quota or reset time
   - Users receive 429 without context on when to retry

**Architectural Inconsistency**:
- Flask-Limiter uses Redis (line 66-73)
- Location change limiting uses in-memory dict (line 76)
- Should migrate `location_changes` to Redis for consistency and multi-instance correctness

## 3. Architecture & Implementation

### Data Flow

```
[HTTP Request to Rate-Limited Endpoint] → [ProxyFix extracts real IP from X-Forwarded-For]
         ↓
[Flask-Limiter intercepts via decorator] → [get_remote_address() returns client IP]
         ↓
[Query Redis: GET rate_limit:{ip}:{endpoint}]
         ↓
[If count < limit]:
    ├─> [INCR rate_limit:{ip}:{endpoint}]
    ├─> [EXPIRE rate_limit:{ip}:{endpoint} {window_seconds}]
    └─> [Allow request → route handler executes]
         ↓
[If count >= limit]:
    └─> [Return 429 Too Many Requests]
```

**Location Change Rate Limiting** (separate, in-memory):
```
[POST /update-location] → [check_location_change_limit(user_id)]
         ↓
[Read location_changes[user_id] from in-memory dict]
         ↓
[Filter timestamps: keep only today's entries]
         ↓
[If len(timestamps) >= 7]:
    └─> [Return error: "Maximum 7 location changes per day reached"]
         ↓
[Else]:
    ├─> [Append current timestamp to location_changes[user_id]]
    └─> [Continue to database update]
```

### Key Components

**Flask-Limiter Configuration** (line 66-73):
```python
limiter = Limiter(
    key_func=get_remote_address,           # IP-based rate limiting
    storage_uri=redis_url,                 # Redis backend via REDIS_URL env var
    storage_options={"socket_connect_timeout": 30},  # 30s timeout
    strategy="fixed-window",               # Window-based counting
)
limiter.init_app(app)                      # Attach to Flask app
```

**Rate Limit Decorators**:
- `@limiter.limit("5 per hour")` - Forgot password endpoint (line 275)
- `@limiter.limit("3 per 15 minutes")` - Login endpoint (line 319)
- `@limiter.limit("10/minute")` - Registration, dashboard, update endpoints (line 388, 447, 593)

**Custom Location Change Limiter** (line 200-220):
```python
def check_location_change_limit(user_id):
    # In-memory dict, NOT Redis
    if user_id not in location_changes:
        location_changes[user_id] = []

    # Prune old timestamps (older than today)
    location_changes[user_id] = [
        ts for ts in location_changes[user_id]
        if ts > today_start
    ]

    # Check limit: 7 per day
    if len(location_changes[user_id]) >= 7:
        return False, "Maximum 7 location changes per day reached"

    # Append timestamp
    location_changes[user_id].append(now)
    return True, "OK"
```

### Configuration

**Environment Variables**:
- `REDIS_URL` (required in production) - Format: `redis://hostname:port`
- Fallback: `redis://localhost:6379` for local development (line 63)
- Provided by Render Redis addon in production

**Hardcoded Configuration**:
- Socket connect timeout: 30 seconds (line 69)
- Rate limit strategy: `fixed-window` (line 70)
- Forgot password: 5 requests per hour (line 275)
- Login: 3 requests per 15 minutes (line 319)
- Registration: 10 requests per minute (line 388)
- Dashboard: 10 requests per minute (line 447, 593)
- Location changes: 7 per day (line 215)

**Flask-Limiter Defaults** (not explicitly configured):
- Connection pool size: Default (unknown, not specified in code)
- Retry logic: Default (unknown, not specified in code)
- Fallback behavior: In-memory storage if Redis unavailable

## 4. Integration Points

### What Calls This Component

**Flask Application**:
- Web server startup initializes limiter (line 73: `limiter.init_app(app)`)
- Rate limit decorators intercept requests before route handlers
- Every request to rate-limited endpoint queries Redis

**No External Callers**:
- Redis not accessed directly by other services
- Only Flask-Limiter library communicates with Redis
- Other components (background processor, Arduinos) don't use Redis

### What This Component Calls

**Redis Server**:
- `GET rate_limit:{key}` - Check current count for IP/endpoint combo
- `INCR rate_limit:{key}` - Increment counter
- `EXPIRE rate_limit:{key} {ttl}` - Set expiration for window reset
- Commands issued by Flask-Limiter library, not application code directly

**ProxyFix Middleware** (app.py line 52):
- `get_remote_address()` relies on `X-Forwarded-For` header extraction
- ProxyFix parses header to get real client IP
- Integration: `key_func=get_remote_address` (line 67)

### Data Contracts

**Redis Key Format** (Flask-Limiter internal):
```
rate_limit:{ip_address}:{endpoint_identifier}
```
Example: `rate_limit:192.168.1.100:/login`

**Redis Value**: Integer counter

**Redis TTL**: Window duration in seconds
- `5 per hour` → 3600 seconds
- `3 per 15 minutes` → 900 seconds
- `10/minute` → 60 seconds

**HTTP Response on Rate Limit Exceeded**:
```
Status: 429 Too Many Requests
Body: "429 Too Many Requests: X per Y"
```

**Location Change Response** (custom limiter):
```python
# Success
(True, "OK")

# Failure
(False, "Maximum 7 location changes per day reached")
```

## 5. Troubleshooting & Failure Modes

### Common Issues

**Problem: Rate Limits Not Working Across Instances**

**Symptoms**: Users can exceed rate limits by making requests rapidly

**Detection**: Check Render instance count - if >1, rate limits per-instance not global

**Causes**:
- `location_changes` dict is in-memory (line 76) - each instance has separate copy
- User hits different instances, each allows 7 location changes = 14 total if 2 instances

**Recovery**:
1. Scale Render to single instance (temporary fix)
2. Migrate `location_changes` to Redis (permanent fix):
   ```python
   # Instead of dict, use Redis
   redis_client = redis.from_url(redis_url)
   key = f"location_changes:{user_id}"
   redis_client.zadd(key, {str(time.time()): time.time()})
   redis_client.zremrangebyscore(key, '-inf', today_start.timestamp())
   count = redis_client.zcard(key)
   ```

**Problem: Redis Connection Timeouts**

**Symptoms**: 30-second delays on web requests, 500 errors if Redis completely unavailable

**Detection**: Check web server logs for Redis connection errors, response time >30s

**Causes**:
- Redis instance down or restarting
- Network issues between Render web service and Redis addon
- Socket timeout too aggressive (line 69: 30 seconds)

**Recovery**:
1. Check Redis status in Render dashboard
2. Verify `REDIS_URL` environment variable set correctly
3. Test Redis connection: `redis-cli -u $REDIS_URL ping` (should return PONG)
4. Increase socket timeout to 60 seconds if network slow
5. Add explicit fallback handling with logging

**Problem: Legitimate Users Getting Rate Limited**

**Symptoms**: Users report 429 errors during normal usage, especially on login endpoint

**Detection**: Monitor 429 response rate, check if clustered by IP (corporate networks)

**Causes**:
- Login limit `3 per 15 minutes` too strict for forgotten passwords (line 319)
- Corporate NAT: Multiple users share IP, one user's failures block others
- Mobile networks: Carrier-grade NAT shares IP across thousands of users

**Recovery**:
1. Increase login limit to `5 per 15 minutes` or `10 per hour`
2. Consider user-based rate limiting (requires authentication before rate limit check)
3. Whitelist known corporate/carrier IP ranges
4. Add bypass mechanism for support-verified users

**Problem: Rate Limit State Lost on Redis Restart**

**Symptoms**: After Redis restart, users who were rate-limited can suddenly make requests again

**Detection**: Check Redis uptime vs rate limit reset timing

**Causes**:
- Redis configured as cache without persistence (default for Render Redis addon)
- Rate limit counters stored in memory only
- Redis restart = all counters reset to 0

**Recovery**:
1. This is expected behavior for cache-style Redis
2. If persistence needed, enable RDB snapshots or AOF in Redis config
3. For rate limiting, ephemeral state is acceptable (30s-60min windows)
4. Document that brief rate limit reset window after Redis restart is normal

**Problem: Memory Leak in location_changes Dict**

**Symptoms**: Web server memory usage grows over time, never decreases

**Detection**: Monitor process memory via Render metrics, check `len(location_changes)` periodically

**Causes**:
- `location_changes` dict never removes user_id keys (line 76, 200-220)
- Only timestamps pruned, not entire user entries
- Inactive users accumulate: 1000 users = 1000 dict entries forever

**Recovery**:
1. Add cleanup logic to remove users with no recent timestamps:
   ```python
   # After pruning timestamps
   if not location_changes[user_id]:
       del location_changes[user_id]
   ```
2. Or migrate entire system to Redis with TTL
3. Restart web service periodically to clear memory (temporary fix)

### Scaling Concerns

**Redis Connection Pool**:
- Current: Default Flask-Limiter pool size (not specified in code)
- At Scale: 1000 req/sec × 100ms avg duration = 100 concurrent connections needed
- Mitigation: Explicitly configure pool: `storage_options={"socket_connect_timeout": 30, "max_connections": 50}`

**Redis Memory Usage**:
- Current: ~1KB per rate limit key × few hundred keys = <1MB
- At Scale: 10k users × 5 endpoints × 1KB = 50MB (acceptable)
- Keys auto-expire via TTL, memory usage stable
- No mitigation needed unless millions of users

**Fixed-Window Burst Issue**:
- Current: 10/minute allows 20 requests in 1 second at window boundary
- At Scale: Coordinated attack at window boundary bypasses limit
- Mitigation: Switch to sliding-window strategy (more Redis ops but smoother limits)

**Location Change Dict Memory**:
- Current: ~100 bytes per user_id × 1000 users = 100KB
- At Scale: 100k users = 10MB (grows unbounded without cleanup)
- Mitigation: Migrate to Redis sorted sets with TTL

---

*Last Updated: 2025-09-30*
*Service: Render Redis Addon*
*Used By: Flask Web Application (Rate Limiting)*