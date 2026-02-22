# Project Specification: Gerstner Wave Animation Engine

## Overview
The goal is to move beyond simple sine-wave oscillations to a multi-vector wave interference model. This will simulate the complex interaction of multiple wave trains (swell + wind chop) on the lamp's LED strips.

## 1. Mathematical Requirements
The engine must simulate the displacement of "water" (brightness/color) using the Gerstner Wave formula. Unlike a simple sine wave, a Gerstner wave displaces points both vertically and horizontally, creating sharper peaks and flatter troughs.

### Wave Summation
The final state of any LED at position `x` at time `t` must be the result of at least **three** independent wave vectors:
1.  **Primary Swell:** Long wavelength, slow speed, high amplitude.
2.  **Secondary Swell:** Medium wavelength, moderate speed, moderate amplitude.
3.  **Wind Chop:** Short wavelength, high speed, low amplitude (highly frequent).

### Parameters to Calculate
For each wave vector $i$, you will need to manage:
*   **Wavenumber ($k_i$):** Related to the wavelength.
*   **Amplitude ($a_i$):** Related to the wave height.
*   **Phase Speed ($v_i$):** How fast the wave moves across the strip.
*   **Steepness ($Q_i$):** A constant that controls how "pointed" the crests are.

The resulting displacement $P(x, t)$ should determine the final brightness level of the LED.

## 2. Visual Behavior
*   **Trochoidal Profile:** The animation must exhibit a trochoidal shape (sharp peaks and broad valleys).
*   **Constructive Interference:** When the peaks of multiple waves align, the LED should reach maximum intensity ("foam" effect).
*   **Destructive Interference:** When waves cancel out, the strip should appear "calm" or darker.
*   **Theme Integration:** The base colors must be pulled from the existing `Themes.h` logic, but the brightness must be dynamically modulated by the wave height calculation.

## 3. Performance Constraints
*   **Execution Target:** Core 1 (Artist Core).
*   **Frame Rate:** Must maintain a stable 200 FPS refresh rate for all 30+ LEDs.
*   **Arithmetic:** You are encouraged to use **Fixed-Point Arithmetic**. Avoid floating-point math in the main render loop to ensure maximum cycle efficiency and prevent FPU contention with Core 0.
*   **Memory:** Minimize dynamic memory allocation; the state should be predictable and stack-resident or pre-allocated.

## 4. Integration Points
*   **Input:** The engine must use the `displayCache` (Wave Height, Period, Wind Speed) to scale the amplitudes and speeds of the generated wave vectors.
*   **Output:** The engine must write directly to the `CRGB leds[]` array.
*   **Location:** Logic should be encapsulated such that it can be triggered within `updateSurfDisplay()` or as a standalone animation mode.

## 5. Success Criteria
1.  The animation loop executes in under 2ms per frame.
2.  The visual output shows non-repeating, organic movement (interference patterns).
3.  The "sharpness" of the wave crests is visually distinct from the smooth trough of a standard sine wave.
4.  No micro-stuttering is observed when the WiFi core (Core 0) performs an HTTP fetch.
