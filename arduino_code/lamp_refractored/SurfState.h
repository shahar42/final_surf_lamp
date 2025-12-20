/*
 * SURF STATE DATA STRUCTURES
 *
 * Centralized data structures for surf lamp state management.
 * Single source of truth for all runtime data.
 *
 * Design principles:
 * - Struct over class (no hidden behavior, simple POD)
 * - Const helpers prevent accidental modification
 * - Clear unit documentation (meters vs cm, m/s vs knots)
 * - Inline conversions = zero runtime cost
 */

#ifndef SURF_STATE_H
#define SURF_STATE_H

#include <Arduino.h>

/**
 * Main surf data structure
 *
 * CRITICAL: All surf conditions stored in consistent units:
 * - waveHeight: meters (converted from cm via /100.0)
 * - waveThreshold: meters (converted from cm via /100.0)
 * - wavePeriod: seconds
 * - windSpeed: m/s
 * - windSpeedThreshold: knots (for user-facing display)
 * - windDirection: degrees (0-360)
 *
 * This ensures proper threshold comparison in updateBlinkingAnimation()
 */
struct SurfData {
    // Surf conditions (stored in consistent units)
    float waveHeight = 0.0;           // Wave height in meters (NOT centimeters!)
    float wavePeriod = 0.0;           // Wave period in seconds
    float windSpeed = 0.0;            // Wind speed in m/s (NOT knots!)
    int windDirection = 0;            // Wind direction in degrees (0-360, 0=North)

    // User preferences/thresholds
    float waveThreshold = 1.0;        // Wave threshold in meters (MUST be float for comparison!)
    int windSpeedThreshold = 15;      // Wind threshold in knots (user-facing unit)
    String theme = "classic_surf";    // LED color theme name
    float brightnessMultiplier = 0.6; // User brightness: 0.3=Low, 0.6=Mid, 1.0=High

    // Operating modes (mutually exclusive priority: off_hours > quiet_hours > normal)
    bool quietHoursActive = false;    // Sleep mode: only top LED of each strip on
    bool offHoursActive = false;      // Off mode: lamp completely dark (highest priority)
    // Legacy fields (removed in V2 - sunset calculated autonomously by SunsetCalculator)
    // bool sunsetTrigger = false;
    // int dayOfYear = 0;

    // State tracking
    unsigned long lastUpdate = 0;     // Timestamp of last data update (millis)
    bool dataReceived = false;        // Has any data been received yet?
    bool needsDisplayUpdate = false;  // Flag to trigger display refresh in loop()

    // Unit conversion helpers (inline = zero overhead, const = no accidental modification)
    int waveHeightCm() const {
        return static_cast<int>(waveHeight * 100);
    }
    int waveThresholdCm() const {
        return static_cast<int>(waveThreshold * 100);
    }
    float waveHeightMeters() const {
        return waveHeight;  // Already in meters, for code clarity
    }
    float waveThresholdMeters() const {
        return waveThreshold;  // Already in meters, for code clarity
    }
};

// Global surf data instance (defined in main .ino file, declared extern here)
// All modules access this single source of truth
extern SurfData lastSurfData;

#endif // SURF_STATE_H
