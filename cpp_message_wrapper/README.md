# Shared Message Wrapper - std::shared_ptr Exercise

## Goal
Wrap existing `SurfData` and `SettingsData` classes (from `my_lib/esp_Server_encoding.hpp`)
with `std::shared_ptr` to enable multi-consumer message sharing.

## What You'll Build

```cpp
// Reuse existing classes - NO bit manipulation needed!
#include "../my_lib/esp_Server_encoding.hpp"

// Wrapper for shared ownership
class ParsedMessage {
public:
    SurfData surf;
    SettingsData settings;
    std::chrono::system_clock::time_point received_at;
};

class MessageHandler {
public:
    // Parse and return shared ownership
    std::shared_ptr<ParsedMessage> parse(const std::vector<uint8_t>& raw_bytes);
};

// Multiple consumers share same message
auto msg = handler.parse(bytes);
logger.log(msg);      // Shares ownership
database.store(msg);  // Shares ownership
broadcast.send(msg);  // Shares ownership
```

## Exercise Focus
- **Shared ownership** with `std::shared_ptr`
- **Reference counting** demonstration
- **Python bindings** for backend integration
- **NO bit manipulation** - reuse existing code

## Files to Implement
1. `include/message_wrapper.h` - ParsedMessage and MessageHandler classes
2. `src/message_wrapper.cpp` - Implementation using existing SurfData/SettingsData
3. `src/bindings.cpp` - pybind11 Python bindings
4. `tests/test_wrapper.cpp` - Shared_ptr usage tests

## Build
TODO: Add CMakeLists.txt and setup.py
