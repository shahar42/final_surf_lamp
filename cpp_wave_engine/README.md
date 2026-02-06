# Wave Calculation Engine

C++ wave calculation library with Python bindings for the Surf Lamp system.

## Structure

```
cpp_wave_engine/
├── CMakeLists.txt          # Build configuration
├── setup.py                # Python package setup
├── include/                # Header files
│   ├── wave_result.h       # Wave calculation result data
│   ├── wave_calculator.h   # Main calculator with caching
│   └── mutex_guard.h       # RAII mutex wrapper
├── src/                    # Implementation
│   ├── wave_calculator.cpp # Calculator implementation
│   └── bindings.cpp        # pybind11 Python bindings
└── tests/                  # Unit tests
    └── test_calculator.cpp # Google Test suite
```

## Build

TODO: Add build instructions

## Integration

TODO: Add integration instructions for surf_data_transformer.py
