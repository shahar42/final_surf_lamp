# Building and Integrating Message Wrapper

## Prerequisites

```bash
# Install dependencies
pip install pybind11 setuptools
sudo apt-get install libgtest-dev cmake

# Optional: Build Google Test
cd /usr/src/gtest
sudo cmake CMakeLists.txt
sudo make
sudo cp *.a /usr/lib
sudo ln -s /usr/src/gtest /usr/src/googletest
```

## Build Steps

### Option 1: Build C++ Library Only (Development)

```bash
cd cpp_message_wrapper
mkdir build && cd build
cmake ..
make
./test_wrapper  # Run unit tests
```

### Option 2: Build Python Package (Production)

```bash
cd cpp_message_wrapper
pip install -e .
```

This will:
1. Compile C++ code with pybind11
2. Generate Python module `message_wrapper`
3. Allow `import message_wrapper` from anywhere

## Integration Steps

### Step 1: Build and Install

```bash
cd cpp_message_wrapper
pip install -e .
```

### Step 2: Test Python Module

```python
import message_wrapper

# Create parser
handler = message_wrapper.MessageHandler()

# Create test message
from cpp_message_wrapper.tests.test_wrapper import getValidTestMessage
raw = getValidTestMessage()

# Parse
msg = handler.parse(raw)
print(f"Wave height: {msg.surf.get_wave_height()}cm")
print(f"Brightness: {msg.settings.get_brightness()}%")
```

### Step 3: Replace Python Parser in Backend

In `web_and_database/blueprints/api_arduino.py`:

**Before (Python parser):**
```python
from web_and_database.binary_protocol import encode_v3_response

raw_bytes = request.get_data()
surf_data = SurfDataEncoder.unpack(raw_bytes[0:8])
settings_data = SettingsDataEncoder.unpack(raw_bytes[9:26])
```

**After (C++ parser):**
```python
from cpp_message_wrapper.integration_example import parse_v3_message_cpp

raw_bytes = request.get_data()
parsed = parse_v3_message_cpp(raw_bytes)
if parsed:
    surf_data = parsed['surf']
    settings_data = parsed['settings']
```

### Step 4: Update Backend Code

Replace parsing calls in these files:
- `web_and_database/blueprints/api_arduino.py` - Arduino message handling
- `web_and_database/data_base.py` - Database updates
- `surf-lamp-processor/background_processor.py` - Background processing

### Step 5: Test Integration

```bash
# Run existing tests
pytest web_and_database/tests/

# New tests with C++ parser
pytest cpp_message_wrapper/tests/test_wrapper.cpp
```

## Performance Comparison

```python
import time
import message_wrapper
from web_and_database.binary_protocol import SurfDataEncoder, SettingsDataEncoder

# Create test message
raw_bytes = b'\x00' * 26  # Placeholder

handler = message_wrapper.MessageHandler()

# C++ Performance
start = time.time()
for _ in range(10000):
    msg = handler.parse(raw_bytes)
cpp_time = time.time() - start

print(f"C++ parser: {cpp_time:.3f}s for 10,000 messages")
print(f"Average: {cpp_time/10000*1000:.3f}ms per message")
```

## Troubleshooting

### Import Error: "No module named 'message_wrapper'"

```bash
# Verify installation
pip list | grep message_wrapper
python -c "import message_wrapper; print(message_wrapper.__file__)"

# Reinstall
pip uninstall message_wrapper
cd cpp_message_wrapper
pip install -e .
```

### Compilation Error

```bash
# Check pybind11 is installed
pip show pybind11

# Check CMake
cmake --version

# Verbose build
pip install -e . -v
```

### Test Failures

```bash
cd cpp_message_wrapper/build
./test_wrapper --gtest_verbose
```

## Docker Integration

```dockerfile
FROM python:3.9

# Install build dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    libgtest-dev

# Build and install message_wrapper
COPY cpp_message_wrapper /app/cpp_message_wrapper
WORKDIR /app/cpp_message_wrapper
RUN pip install pybind11 setuptools
RUN pip install -e .

# Copy backend
COPY web_and_database /app/web_and_database
WORKDIR /app
```

## Version Compatibility

- C++: 17 or later
- Python: 3.8+
- pybind11: 2.7+
- GTest: 1.11+

## Future Improvements

- [ ] Add async parsing for high-throughput scenarios
- [ ] Add message batching (parse 10 messages efficiently)
- [ ] Add performance profiling hooks
- [ ] Add optional compression for storage
