/*
 * FAST SIN LOOKUP TABLE
 * author: Shahar
 * date: 6/2/2026
 * 
 * Replaces expensive sin() calls (~100 cycles) with table lookup (~3 cycles).
 * 256-entry table covers 0 to 2*PI with ~1.4% max error - imperceptible for LED animations.
 */

#ifndef FAST_SIN_H
#define FAST_SIN_H

#include <cstdint>

namespace FastMath {

// 256-entry lookup table: sin(i * 2*PI / 256) scaled to [-127, 127]
// Using int8_t to save RAM (256 bytes vs 1024 for float)
static constexpr int8_t SIN_LUT[256] = {
    0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45,
    48, 51, 54, 57, 59, 62, 65, 67, 70, 73, 75, 78, 80, 82, 85, 87,
    89, 91, 94, 96, 98, 100, 102, 103, 105, 107, 108, 110, 112, 113, 114, 116,
    117, 118, 119, 120, 121, 122, 123, 123, 124, 125, 125, 126, 126, 126, 126, 126,
    127, 126, 126, 126, 126, 126, 125, 125, 124, 123, 123, 122, 121, 120, 119, 118,
    117, 116, 114, 113, 112, 110, 108, 107, 105, 103, 102, 100, 98, 96, 94, 91,
    89, 87, 85, 82, 80, 78, 75, 73, 70, 67, 65, 62, 59, 57, 54, 51,
    48, 45, 42, 39, 36, 33, 30, 27, 24, 21, 18, 15, 12, 9, 6, 3,
    0, -3, -6, -9, -12, -15, -18, -21, -24, -27, -30, -33, -36, -39, -42, -45,
    -48, -51, -54, -57, -59, -62, -65, -67, -70, -73, -75, -78, -80, -82, -85, -87,
    -89, -91, -94, -96, -98, -100, -102, -103, -105, -107, -108, -110, -112, -113, -114, -116,
    -117, -118, -119, -120, -121, -122, -123, -123, -124, -125, -125, -126, -126, -126, -126, -126,
    -127, -126, -126, -126, -126, -126, -125, -125, -124, -123, -123, -122, -121, -120, -119, -118,
    -117, -116, -114, -113, -112, -110, -108, -107, -105, -103, -102, -100, -98, -96, -94, -91,
    -89, -87, -85, -82, -80, -78, -75, -73, -70, -67, -65, -62, -59, -57, -54, -51,
    -48, -45, -42, -39, -36, -33, -30, -27, -24, -21, -18, -15, -12, -9, -6, -3
};

// Scale factor for converting radians to LUT index: 256 / (2*PI) ≈ 40.74
static constexpr float RAD_TO_INDEX = 40.743665f;

/**
 * Fast sine approximation using lookup table.
 * @param radians Input angle in radians
 * @return Sine value in range [-1.0, 1.0]
 */
inline float fastSin(float radians) {
    // Convert radians to table index (0-255), with wraparound
    int index = static_cast<int>(radians * RAD_TO_INDEX) & 0xFF;
    return SIN_LUT[index] / 127.0f;
}

/**
 * Fast sine returning 0-1 range (for brightness calculations).
 * Equivalent to (sin(x) + 1) / 2
 * @param radians Input angle in radians
 * @return Value in range [0.0, 1.0]
 */
inline float fastSin01(float radians) {
    int index = static_cast<int>(radians * RAD_TO_INDEX) & 0xFF;
    return (SIN_LUT[index] + 127) / 254.0f;
}

} // namespace FastMath

#endif // FAST_SIN_H
