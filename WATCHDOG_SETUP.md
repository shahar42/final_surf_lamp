# Processor Watchdog Setup Guide

## Architecture

Based on the bidirectional watchdog pattern from `~/git/utils/watch_dog/`:

```
PROCESSOR (Background Worker)          WATCHDOG MONITOR (Cron/Script)
========================              ===========================
Every 60s:                            Every 120s:
- Write heartbeat to DB               - Check DB timestamp
  (last_alive_timestamp)                - If stale (>180s):
- Reset missed_count = 0                  - Increment missed_count
                                          - If missed_count > 3:
                                            - Restart via Render API
                                            - Increment revive_count
                                            - Stop if revive_count >= 3
```

## Setup Instructions

### 1. Create Database Table

Run this in **Supabase SQL Editor**:

```sql
-- Run: migration_add_processor_heartbeat.sql
CREATE TABLE IF NOT EXISTS processor_heartbeat (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL UNIQUE,
    last_alive_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    missed_count INTEGER DEFAULT 0,
    revive_count INTEGER DEFAULT 0,
    max_revives INTEGER DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO processor_heartbeat (service_name, last_alive_timestamp)
VALUES ('surf-lamp-processor', NOW())
ON CONFLICT (service_name) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_processor_heartbeat_service ON processor_heartbeat(service_name);
```

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Watchdog Configuration
RENDER_PROCESSOR_SERVICE_ID=srv-d5eerd9r0fns73d52t80
RENDER_API_KEY=rnd_j6WyOXSMG0bGFbqyYKMBaxUgzF4s  # (Already exists)
```

### 3. Deploy Processor Changes

The processor now writes heartbeats every 60 seconds automatically.

```bash
cd surf-lamp-processor
git add .
git commit -m "feat: add watchdog heartbeat writer"
git push
# Render will auto-deploy
```

### 4. Run Watchdog Monitor

**Option A: Local Testing**
```bash
python processor_watchdog.py
```

**Option B: Production (Cron)**
```bash
# Add to crontab (runs every 2 minutes)
*/2 * * * * cd /home/shahar42/Git_Surf_Lamp_Agent && /usr/bin/python3 processor_watchdog.py >> watchdog_monitor.log 2>&1
```

**Option C: Separate Render Service** (Recommended for production)
Create a second background worker that runs the watchdog monitor 24/7.

## How It Works

### Constants (from C implementation)
- **T_INTERVAL**: 120s (2 minutes between checks)
- **MAX_MISSED_PINGS**: 3 (allow 3 missed heartbeats before restart)
- **MAX_REVIVES**: 3 (stop after 3 restart attempts)
- **Staleness Threshold**: 180s (3 minutes without heartbeat = hung)

### State Machine

```
HEALTHY → STALE → MISSED_1 → MISSED_2 → MISSED_3 → MISSED_4 → RESTART
                                                                    ↓
                                                            REVIVE_COUNT++
                                                                    ↓
                                                            If < MAX_REVIVES:
                                                              Reset missed_count
                                                            Else:
                                                              STOP WATCHDOG
```

### Recovery Flow

1. Processor stops writing heartbeats (hung/crashed)
2. Watchdog detects staleness after 180s
3. Watchdog increments missed_count every 120s
4. After 4th missed ping (480s = 8 minutes total), trigger restart
5. Render restarts processor → heartbeat resumes
6. Watchdog resets missed_count

### Safety Mechanisms

- **Max Revives**: Prevents infinite restart loops (stops after 3 attempts)
- **Gradual Detection**: Requires 4 consecutive failures before restart
- **Database State**: All state persists in DB (survives watchdog restarts)
- **Manual Override**: Can reset revive_count manually in DB to re-enable

## Monitoring

Check watchdog status:
```sql
SELECT * FROM processor_heartbeat;
```

Manual reset if needed:
```sql
UPDATE processor_heartbeat
SET revive_count = 0, missed_count = 0
WHERE service_name = 'surf-lamp-processor';
```

## Testing

Simulate hung processor:
```bash
# Stop the processor manually on Render
# Watch watchdog detect and restart it
tail -f watchdog_monitor.log
```
