# Load Test Implementation Pseudo Code

## 1. Arduino Simulator (locustfile.py)

```python
# SETUP
import locust, random, time

# 1000 Arduino IDs (10001-11000)
ARDUINO_IDS = range(10001, 11001)

class ArduinoSimulator(HttpUser):
    # Poll every 13 minutes ± 20 seconds variance
    wait_time = between(780, 820)

    def on_start():
        # Assign unique Arduino ID to this virtual user
        self.arduino_id = pick_random_from_pool(ARDUINO_IDS)
        remove_from_pool(self.arduino_id)  # Prevent duplicates

    @task
    def poll_api():
        # GET /api/arduino/{id}/data
        response = http_get(f"/api/arduino/{self.arduino_id}/data")

        # Validate response
        assert response.status == 200
        assert response.json has keys: [wave_height, wave_period, wind_speed, wind_direction]

        # Locust auto-tracks response time, success rate
```

**Run command:**
```bash
locust --host=https://final-surf-lamp-web.onrender.com \
       --users=1000 \
       --spawn-rate=0.56 \
       --run-time=6h \
       --html=results/locust_report.html
```

---

## 2. Background Processor Test (background_processor_test.py)

```python
# SETUP
import time, json, sys
sys.path.append('../surf-lamp-processor')
from background_processor import get_location_based_configs, process_location

# Constants
CYCLES = 24                    # 6 hours / 15 min intervals
CYCLE_INTERVAL_SEC = 900       # 15 minutes
MAX_ALLOWED_CYCLE_TIME = 850   # Leave 50 sec buffer

def measure_cycle():
    start = time.time()

    # Get locations to process
    location_configs = get_location_based_configs()

    # Process each location
    location_times = {}
    for location, config in location_configs.items():
        location_start = time.time()
        process_location(location, config)
        location_times[location] = time.time() - location_start

    total_time = time.time() - start

    return {
        'total_seconds': total_time,
        'locations_processed': len(location_configs),
        'location_breakdown': location_times,
        'exceeded_limit': total_time > MAX_ALLOWED_CYCLE_TIME
    }

def run_test():
    results = []

    for cycle in range(1, CYCLES + 1):
        print(f"Cycle {cycle}/{CYCLES} starting...")

        cycle_result = measure_cycle()
        cycle_result['cycle_number'] = cycle
        cycle_result['timestamp'] = datetime.now().isoformat()

        results.append(cycle_result)

        # Log warnings
        if cycle_result['exceeded_limit']:
            print(f"⚠️  CYCLE {cycle} EXCEEDED LIMIT: {cycle_result['total_seconds']}s")

        # Sleep until next cycle
        sleep_time = CYCLE_INTERVAL_SEC - cycle_result['total_seconds']
        if sleep_time > 0:
            time.sleep(sleep_time)
        else:
            print(f"❌ CYCLE {cycle} DRIFT: No time to sleep!")

    # Save results
    with open('results/processor_test.json', 'w') as f:
        json.dump(results, f, indent=2)

    # Calculate statistics
    avg_time = sum(r['total_seconds'] for r in results) / len(results)
    max_time = max(r['total_seconds'] for r in results)
    failures = sum(1 for r in results if r['exceeded_limit'])

    print("\n=== PROCESSOR TEST RESULTS ===")
    print(f"Average cycle time: {avg_time:.2f}s")
    print(f"Max cycle time: {max_time:.2f}s")
    print(f"Cycles exceeding limit: {failures}/{CYCLES}")

    return failures == 0  # Pass if no cycles exceeded limit
```

---

## 3. Database Monitor (database_monitor.py)

```python
# SETUP
import psycopg2, time, json

def monitor_pool():
    """Run in background during load test"""

    metrics = []

    while test_running:
        # Query Supabase pool stats (if accessible)
        # OR query local test DB: SELECT * FROM pg_stat_activity

        stats = {
            'timestamp': time.time(),
            'active_connections': query("SELECT count(*) FROM pg_stat_activity WHERE state='active'"),
            'idle_connections': query("SELECT count(*) FROM pg_stat_activity WHERE state='idle'"),
            'waiting_queries': query("SELECT count(*) FROM pg_stat_activity WHERE wait_event IS NOT NULL")
        }

        metrics.append(stats)

        # Alert if pool saturated
        if stats['active_connections'] > POOL_SIZE * 0.9:
            print(f"⚠️  Pool near capacity: {stats['active_connections']}/{POOL_SIZE}")

        time.sleep(10)  # Sample every 10 seconds

    # Save metrics
    save_json('results/db_pool_metrics.json', metrics)
```

---

## 4. Metrics Collector (metrics_collector.py)

```python
# SETUP
from locust import events

# Track custom metrics
request_times = []
error_count = 0

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Capture every request"""

    if exception:
        error_count += 1
        log_error(name, exception)
    else:
        request_times.append({
            'endpoint': name,
            'response_ms': response_time,
            'timestamp': time.time()
        })

@events.test_stop.add_listener
def on_test_stop(**kwargs):
    """Calculate final statistics"""

    # Percentiles
    p50 = percentile(request_times, 50)
    p95 = percentile(request_times, 95)
    p99 = percentile(request_times, 99)

    report = {
        'total_requests': len(request_times),
        'total_errors': error_count,
        'error_rate': error_count / len(request_times),
        'response_time_p50': p50,
        'response_time_p95': p95,
        'response_time_p99': p99
    }

    save_json('results/metrics_summary.json', report)
    print_summary(report)
```

---

## 5. Orchestration Script (run_load_test.sh)

```bash
#!/bin/bash
set -e

echo "=== Starting 6-Hour Load Test ==="

# Step 1: Environment setup
echo "[1/7] Starting test database (Docker)..."
docker-compose up -d
sleep 5

echo "[2/7] Creating schema..."
python -c "from data_base import Base; Base.metadata.create_all(engine)"

echo "[3/7] Seeding 1000 test lamps..."
python seed_database.py

# Step 2: Start monitoring
echo "[4/7] Starting database pool monitor..."
python database_monitor.py &
DB_MONITOR_PID=$!

echo "[5/7] Starting Flask test server..."
FLASK_ENV=testing python ../web_and_database/app.py &
FLASK_PID=$!
sleep 3

# Step 3: Run tests in parallel
echo "[6/7] Starting Locust (1000 Arduinos × 6 hours)..."
locust --host=http://localhost:5001 \
       --users=1000 \
       --spawn-rate=0.56 \
       --run-time=6h \
       --html=results/locust_report.html \
       --headless &
LOCUST_PID=$!

echo "[6/7] Starting background processor test (24 cycles)..."
python background_processor_test.py &
PROCESSOR_PID=$!

# Step 4: Wait for completion
wait $LOCUST_PID
wait $PROCESSOR_PID

# Step 5: Cleanup
echo "[7/7] Cleaning up..."
kill $FLASK_PID $DB_MONITOR_PID
docker-compose down

echo "✅ Load test complete - results in tools/load-testing/results/"
echo "   - locust_report.html (API performance)"
echo "   - processor_test.json (cycle times)"
echo "   - db_pool_metrics.json (database load)"
```

---

## 6. Database Seeding (seed_database.py)

```python
# SETUP
from data_base import engine, User, Lamp
from sqlalchemy.orm import Session

def seed_test_data():
    """Create 1000 lamps across realistic locations"""

    locations = [
        ("Tel Aviv, Israel", 150),
        ("Haifa, Israel", 120),
        ("Netanya, Israel", 100),
        # ... more locations totaling 1000
    ]

    session = Session(engine)

    lamp_id = 10001
    for location, count in locations:
        for i in range(count):
            # Create user for this lamp
            user = User(
                username=f"test_user_{lamp_id}",
                email=f"test{lamp_id}@example.com",
                location=location,
                wave_threshold_m=2.0,
                wind_threshold_knots=22.0
            )
            session.add(user)
            session.flush()

            # Create lamp
            lamp = Lamp(
                user_id=user.user_id,
                arduino_id=lamp_id
            )
            session.add(lamp)

            lamp_id += 1

    session.commit()
    print(f"✅ Seeded {lamp_id - 10001} test lamps")
```

---

## Success Criteria

**PASS if ALL conditions met:**
1. Locust error rate < 1%
2. P95 response time < 500ms
3. P99 response time < 1000ms
4. All 24 processor cycles complete in < 14 min each
5. No database connection pool exhaustion
6. No memory leaks (Flask memory stable over 6 hours)

**FAIL if ANY:**
- Error rate > 5%
- Any processor cycle > 15 minutes
- Database connections maxed out
- Flask crashes or OOM
