# C/C++ Performance Optimization Projects

These projects focus on "root" performance improvements, moving heavy lifting from Python to C++ or optimizing ESP32 execution for smoother real-time performance.

## 1. Gerstner Wave Animation Engine (ESP32)
**Goal:** Replace simple sine-wave blinking with realistic water surface simulation.

*   **The Challenge:** Implement a Gerstner Wave summation algorithm (summing 3-4 wave vectors) to calculate LED brightness and color.
*   **Performance Requirement:** Use **fixed-point math** (integer arithmetic) instead of `float`. ESP32's FPU is fast, but fixed-point is faster for bulk animations and avoids precision jitter.
*   **Visual Target:** Waves should have "sharp" crests and "broad" troughs, simulated by the Gerstner formula: 
    `y = a * sin(dot(w, x) + phi)`
*   **File:** `arduino_code/lamp_refractored/lamp_template/LedController.cpp`

## 2. Batch JSON-to-Binary Transformer (Server Extension)
**Goal:** Optimize server-side encoding for 10,000+ simultaneous lamp requests.

*   **The Challenge:** Create a C++ function that takes a large JSON array of surf conditions and user settings, parses them, and packs them into a single contiguous binary buffer of V3 packets (26 bytes each).
*   **Performance Requirement:** Use a high-performance C++ JSON library (like `simdjson` or `rapidjson`) to bypass Python's slow dictionary iterations.
*   **Impact:** Drastically reduces memory allocation overhead and GIL contention during high-traffic windows.
*   **File:** `cpp_message_wrapper/src/message_wrapper.cpp`

## 3. Zero-Copy Inter-Core Ring Buffer (ESP32)
**Goal:** Eliminate animation micro-stuttering caused by mutex contention.

*   **The Challenge:** Implement a **Single-Producer Single-Consumer (SPSC) Lock-Free Ring Buffer** to pass `SurfData` from Core 0 (Secretary) to Core 1 (Artist).
*   **Performance Requirement:** Use `std::atomic` with `memory_order_acquire/release` to ensure data visibility without using heavy FreeRTOS mutexes or semaphores.
*   **Impact:** Core 1 will never "wait" for Core 0 to finish a slow network task, ensuring the 200 FPS animation loop remains perfectly consistent.
*   **File:** `my_lib/my_linear_buffer.hpp`
