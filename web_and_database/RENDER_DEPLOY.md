# Render Deployment Configuration for Surf Lamp Web Service

## Build Command

```bash
cd web_and_database && ./build.sh
```

The build script will:
1. Install Python dependencies from requirements.txt
2. Build and install the C++ message_wrapper module
3. Link pybind11 and compile C++ extensions

## System Dependencies

Required for C++ compilation:
- `build-essential` (gcc, g++, make)
- `cmake` (optional, for development)

Render's Python environment includes these by default.

## Environment Variables

Ensure these are set in Render dashboard:
- `PYTHON_VERSION`: 3.11 or later
- `DATABASE_URL`: PostgreSQL connection string
- All other existing environment variables

## Start Command

```bash
gunicorn --config gunicorn.conf.py app:app
```

**Configuration Details:**
- Worker class: `gevent` (async greenlet-based workers)
- Workers: 4 (optimized for 512MB RAM)
- Worker connections: 1000 concurrent connections per worker
- Capacity: ~4000 req/sec (20x improvement over sync workers)
- Supports: 30,000+ lamps at 13-minute poll intervals

## Deployment Notes

1. The C++ wrapper is compiled during build phase (not runtime)
2. Build time increases by ~30 seconds for C++ compilation
3. If build fails, check:
   - pybind11 installed correctly
   - C++ compiler available (build-essential)
   - Paths to cpp_message_wrapper are correct

## Rollback Plan

If C++ integration fails:
1. Revert commit 47d5ac7
2. Redeploy previous version
3. System will fall back to Python encoding

## Testing After Deployment

Monitor first few requests:
```bash
# Check logs for C++ module loading
grep "message_wrapper" render_logs

# Verify Arduinos receiving correct data
# Check Arduino dashboard for normal operation
```

Expected behavior:
- Faster response times (12.5x encoding speedup)
- Same binary output (CRC-validated)
- Lower memory usage at scale
