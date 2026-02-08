# Threshold Calculator - C Implementation Tasks

## Phase 1: Core Implementation
- [ ] **threshold_calc.h** - Write function declaration
  - Function signature: `double calculate_effective_threshold(double current_value, double user_min, double user_max)`
  - Constants: `#define IMPOSSIBLE_THRESHOLD 9999.0`
  - Include guards

- [ ] **threshold_calc.c** - Write implementation
  - Handle NULL case: `current_value == -1.0` → return `user_min`
  - Handle backwards compatibility: `user_max == -1.0` → return `user_min`
  - Handle above max: `current_value > user_max` → return `IMPOSSIBLE_THRESHOLD`
  - Default case: return `user_min`

## Phase 2: Testing
- [ ] **test_threshold.c** - Write test suite
  - Test 1: Traditional mode (no max) → `calc(2.5, 1.0, -1.0)` = `1.0`
  - Test 2: Within range → `calc(2.0, 1.0, 3.0)` = `1.0`
  - Test 3: Below min → `calc(0.5, 1.0, 3.0)` = `1.0`
  - Test 4: Above max → `calc(4.0, 1.0, 3.0)` = `9999.0`
  - Test 5: NULL current → `calc(-1.0, 1.0, 3.0)` = `1.0`
  - Print test results (PASS/FAIL)

- [ ] **Local compilation test**
  ```bash
  cd web_and_database/threshold_calc
  gcc -o test_threshold threshold_calc.c test_threshold.c
  ./test_threshold
  ```

## Phase 3: Python Integration
- [ ] **threshold_calc_wrapper.py** - Create ctypes wrapper
  - Load `libthreshold.so` using ctypes.CDLL
  - Define function signature (argtypes, restype)
  - Create Python wrapper function that converts None → -1.0
  - Add fallback to Python implementation if .so not found

- [ ] **Update threshold_logic.py**
  - Import C wrapper at top
  - Add try/except to use C version, fallback to Python
  - Keep original Python function as fallback

## Phase 4: Build System
- [ ] **Update web_and_database/build.sh**
  - Add compilation step after merge sort section:
    ```bash
    echo "🧮 Compiling Threshold Calculator..."
    cd "$PROJECT_ROOT/web_and_database/threshold_calc"
    gcc -shared -fPIC -O3 threshold_calc.c -o libthreshold.so
    echo "✅ Threshold calculator compiled!"
    ```

## Phase 5: Deployment & Testing
- [ ] **Test locally**
  - Run build.sh
  - Verify libthreshold.so is created
  - Test Python import: `from utils.threshold_calc_wrapper import calculate_effective_threshold_c`
  - Run manual tests with different inputs

- [ ] **Integration test**
  - Test with actual arduino API calls
  - Verify threshold calculations are correct
  - Check performance improvement (optional)

- [ ] **Deploy to Render**
  - Commit all files
  - Push to trigger deployment
  - Monitor deployment logs for compilation success
  - Verify production works correctly

## Reference Files
- **Merge sort example:** `surf-lamp-processor/merge_sort/mergesort.c`
- **Python function to replicate:** `web_and_database/utils/threshold_logic.py:24`
- **Integration point:** `web_and_database/blueprints/api_arduino.py:136` (calculate_thresholds function)

## Expected Performance
- **Current:** Pure Python, ~0.01ms per call
- **Target:** C implementation, ~0.001ms per call (10x faster)
- **Impact:** Called 100+ times per minute across all arduino polls
