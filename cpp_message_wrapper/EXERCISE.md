# EXERCISE: Message Wrapper with Shared Ownership

## Classification
Training Exercise - C++ Smart Pointers (std::shared_ptr)

## Objective
Demonstrate proficiency in `std::shared_ptr` ownership semantics by wrapping existing
binary protocol classes for multi-consumer message distribution. This exercise focuses
exclusively on smart pointer usage, NOT bit manipulation.

## Background
The Surf Lamp Arduino sends 26-byte binary messages to the Python backend. Currently,
the parsing logic exists in C++ (`my_lib/esp_Server_encoding.hpp`) with classes:
- `SurfData` - Surf conditions (9 bytes: 8 data + 1 CRC)
- `SettingsData` - User settings (17 bytes: 16 data + 1 CRC)

Backend services (logger, database, broadcaster) need access to the same parsed message.
Your task: wrap these existing classes with `std::shared_ptr` to enable shared ownership
without copying data.

## Technical Requirements

### 1. Data Structure (message_wrapper.h)

```cpp
#include "../../my_lib/esp_Server_encoding.hpp"
#include <memory>
#include <chrono>

class ParsedMessage {
public:
    ParsedMessage(const SurfData& surf, const SettingsData& settings);

    SurfData surf;
    SettingsData settings;
    std::chrono::system_clock::time_point received_at;
};
```

**Requirements:**
- Store existing `SurfData` and `SettingsData` instances
- Timestamp when message was parsed
- Immutable after construction (const members preferred)

### 2. Message Handler (message_wrapper.h)

```cpp
class MessageHandler {
public:
    MessageHandler();

    // Parse 26-byte message, return shared ownership
    // Returns nullptr on validation failure
    std::shared_ptr<ParsedMessage> parse(const std::vector<uint8_t>& raw_bytes);

    // Statistics
    uint64_t getTotalParsed() const;
    uint64_t getValidationFailures() const;

private:
    std::atomic<uint64_t> total_parsed_{0};
    std::atomic<uint64_t> validation_failures_{0};
};
```

**Implementation Steps:**

```cpp
std::shared_ptr<ParsedMessage> MessageHandler::parse(const std::vector<uint8_t>& raw) {
    // 1. Validate size
    if (raw.size() != 26) {
        validation_failures_++;
        return nullptr;
    }

    // 2. Extract bytes 0-7 as big-endian uint64_t
    uint64_t surf_data = 0;
    for (int i = 0; i < 8; i++) {
        surf_data |= ((uint64_t)raw[i] << (56 - i*8));
    }

    // 3. Create SurfData using existing constructor
    SurfData surf(surf_data);

    // 4. Validate CRC (byte 8) using existing method
    if (!surf.ValidateCRC(raw[8])) {
        validation_failures_++;
        return nullptr;
    }

    // 5. Extract bytes 9-16 and 17-24 for SettingsData
    uint64_t settings_data1 = 0;
    uint64_t settings_data2 = 0;
    for (int i = 0; i < 8; i++) {
        settings_data1 |= ((uint64_t)raw[9+i] << (56 - i*8));
        settings_data2 |= ((uint64_t)raw[17+i] << (56 - i*8));
    }

    // 6. Create SettingsData using existing constructor
    SettingsData settings(settings_data1, settings_data2);

    // 7. Validate CRC (byte 25)
    if (!settings.ValidateCRC(raw[25])) {
        validation_failures_++;
        return nullptr;
    }

    // 8. Create ParsedMessage and wrap in shared_ptr
    total_parsed_++;
    return std::make_shared<ParsedMessage>(surf, settings);
}
```

### 3. Python Bindings (bindings.cpp)

```python
import message_wrapper

handler = message_wrapper.MessageHandler()

# Parse 26-byte message
raw_bytes = bytes([...])  # From Arduino
msg = handler.parse(raw_bytes)

if msg is None:
    print("Validation failed")
else:
    # Access via existing SurfData methods
    print(f"Wave: {msg.surf.GetWaveHeight()}cm")
    print(f"Period: {msg.surf.GetWavePeriod()}s")
    print(f"Wind: {msg.surf.GetWindSpeed()}m/s")

    # Access via existing SettingsData methods
    print(f"Brightness: {msg.settings.GetBrightness()}%")
    print(f"GPS: ({msg.settings.GetLatitude()}, {msg.settings.GetLongitude()})")
```

**Requirements:**
- Module name: `message_wrapper`
- Expose `MessageHandler` and `ParsedMessage`
- Expose existing `SurfData` and `SettingsData` methods as properties
- Convert `nullptr` to Python `None`
- Convert `std::chrono::time_point` to `datetime`

### 4. Unit Tests (test_wrapper.cpp)

**Test Cases:**

```cpp
TEST(MessageWrapperTest, SharedOwnership) {
    MessageHandler handler;
    std::vector<uint8_t> raw_bytes = getTestMessage();  // Valid 26 bytes

    auto msg1 = handler.parse(raw_bytes);
    ASSERT_NE(msg1, nullptr);
    EXPECT_EQ(msg1.use_count(), 1);

    // Simulate multiple consumers
    auto msg2 = msg1;  // Logger holds reference
    auto msg3 = msg1;  // Database holds reference
    auto msg4 = msg1;  // Broadcaster holds reference

    // All point to SAME object (pointer equality)
    EXPECT_EQ(msg1.get(), msg2.get());
    EXPECT_EQ(msg1.get(), msg3.get());
    EXPECT_EQ(msg1.get(), msg4.get());

    // Reference count = 4
    EXPECT_EQ(msg1.use_count(), 4);

    // Drop consumer references
    msg2.reset();
    EXPECT_EQ(msg1.use_count(), 3);

    msg3.reset();
    msg4.reset();
    EXPECT_EQ(msg1.use_count(), 1);

    // Original still valid - access data
    EXPECT_EQ(msg1->surf.GetWaveHeight(), 150);
}

TEST(MessageWrapperTest, HandlerLifetime) {
    std::shared_ptr<ParsedMessage> msg;

    {
        MessageHandler handler;
        std::vector<uint8_t> raw = getTestMessage();
        msg = handler.parse(raw);
        ASSERT_NE(msg, nullptr);
    }  // handler destroyed

    // Message still valid! Shared ownership kept it alive
    EXPECT_EQ(msg.use_count(), 1);
    EXPECT_EQ(msg->surf.GetWavePeriod(), 12);
}

TEST(MessageWrapperTest, InvalidCRC) {
    MessageHandler handler;
    std::vector<uint8_t> raw = getTestMessage();

    // Corrupt surf CRC
    raw[8] ^= 0xFF;

    auto msg = handler.parse(raw);
    EXPECT_EQ(msg, nullptr);
    EXPECT_EQ(handler.getValidationFailures(), 1);
}

TEST(MessageWrapperTest, ValidMessage) {
    MessageHandler handler;

    // Generate test vector using Python encoder:
    // from web_and_database.binary_protocol import encode_v3_response
    std::vector<uint8_t> raw = {
        // TODO: Insert actual test vector
    };

    auto msg = handler.parse(raw);
    ASSERT_NE(msg, nullptr);

    // Verify fields using existing getters
    EXPECT_EQ(msg->surf.GetWaveHeight(), 150);
    EXPECT_EQ(msg->surf.GetWavePeriod(), 12);
    EXPECT_EQ(msg->settings.GetBrightness(), 80);
}
```

**Additional Tests:**
- `Statistics` - Verify counters increment correctly
- `TooShort` - 25-byte message returns nullptr
- `TooLong` - 27-byte message returns nullptr
- `MultipleParses` - Each parse creates new shared_ptr

### 5. Build System

#### CMakeLists.txt
```cmake
cmake_minimum_required(VERSION 3.15)
project(message_wrapper)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Werror")

# Include my_lib for existing protocol classes
include_directories(${CMAKE_SOURCE_DIR}/../my_lib)

# Main library
add_library(message_wrapper SHARED
    src/message_wrapper.cpp
)
target_include_directories(message_wrapper PUBLIC include)

# Google Test
find_package(GTest REQUIRED)
add_executable(test_wrapper tests/test_wrapper.cpp)
target_link_libraries(test_wrapper message_wrapper GTest::GTest GTest::Main)

# Python bindings
find_package(pybind11)
if(pybind11_FOUND)
    pybind11_add_module(message_wrapper_py src/bindings.cpp)
    target_link_libraries(message_wrapper_py PRIVATE message_wrapper)
    set_target_properties(message_wrapper_py PROPERTIES OUTPUT_NAME message_wrapper)
endif()
```

#### setup.py
```python
from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        "message_wrapper",
        ["src/bindings.cpp", "src/message_wrapper.cpp"],
        include_dirs=["include", "../my_lib"],
        cxx_std=17,
    ),
]

setup(
    name="message_wrapper",
    version="1.0.0",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
```

## Deliverables

1. **Source Code** - Complete implementation
2. **Unit Tests** - All tests passing
3. **Test Vector** - Generate using Python encoder:
   ```python
   from web_and_database.binary_protocol import encode_v3_response

   surf = {
       'wave_period_s': 12,
       'wave_height_cm': 150,
       'wave_threshold_cm': 100,
       'wind_speed_mps': 25,
       'wind_speed_threshold_knots': 20,
       'wind_direction_deg': 180,
       'stale_data_warning': False,
       'data_available': True,
       'quiet_hours_active': False,
       'off_hours_active': False
   }

   settings = {
       'led_theme': 'classic_surf',
       'brightness_multiplier': 0.8,
       'fetch_interval_ms': 300000,
       'latitude': 32.45,
       'longitude': 34.91,
       'tz_offset': 10800
   }

   raw = encode_v3_response(surf, settings)
   print([f"0x{b:02x}" for b in raw])
   ```

4. **Python Integration Demo** - Script showing:
   - Parse message
   - Multiple consumers share ownership
   - Verify use_count behavior
   - Access data via existing methods

## Acceptance Criteria

- [ ] Code compiles without warnings
- [ ] All unit tests pass
- [ ] Shared ownership test demonstrates use_count correctly
- [ ] Message survives handler destruction
- [ ] CRC validation works (using existing methods)
- [ ] Python bindings import successfully
- [ ] Test vector matches Python encoder output
- [ ] No memory leaks (valgrind clean)

## Learning Objectives

**Why std::shared_ptr for this use case?**

Answer in your README:
1. **Multi-consumer pattern** - Logger, database, broadcaster all need message
2. **No lifetime coordination** - Each consumer independently decides when done
3. **Zero-copy sharing** - No message duplication across consumers
4. **Automatic cleanup** - Last consumer drops reference → memory freed

**Alternative approaches and why they fail:**
- **Raw pointers** - Who owns? Who deletes? Unsafe.
- **unique_ptr** - Can't share, forces copying
- **Copying ParsedMessage** - Wasteful, defeats purpose

## Resources

- **Existing protocol classes:** `my_lib/esp_Server_encoding.hpp`
- **Python encoder:** `web_and_database/binary_protocol.py`
- **Protocol spec:** `web_and_database/V3_BINARY_PROTOCOL.md`

## Estimated Effort
**8-12 hours** across 3 checkpoints:
- Checkpoint 1 (3h): MessageHandler implementation + byte extraction
- Checkpoint 2 (3h): Unit tests with shared_ptr semantics
- Checkpoint 3 (4h): Python bindings + integration demo

## Evaluation Criteria
- **Correctness (40%)** - Tests pass, validation works, no leaks
- **Smart Pointer Usage (40%)** - Proper shared_ptr semantics demonstrated
- **Integration (20%)** - Python bindings work, test vector valid

---

**Start with Checkpoint 1:** Implement `MessageHandler::parse()` and verify with a simple
C++ main() that prints parsed fields. Once that works, move to unit tests.

Good luck!
