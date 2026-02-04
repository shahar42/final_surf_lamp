# Render Deployment Configuration for Surf Lamp Web Service

## Build Command

```bash
./build.sh
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
gunicorn app:app
```

(No changes needed from existing configuration)

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
