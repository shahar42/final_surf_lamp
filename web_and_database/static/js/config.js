/**
 * Dashboard Configuration
 * Centralized configuration for all magic numbers and constants
 */

const DashboardConfig = {
    // LED Hardware Configuration
    LED: {
        NUM_LEDS_CENTER: 20,    // Wind speed strip (center)
        NUM_LEDS_RIGHT: 15,     // Wave height strip (right)
        NUM_LEDS_LEFT: 15,      // Wave period strip (left)
        LED_RADIUS: 8,          // Pixel radius for each LED circle

        // LED strip indices (Arduino matches)
        CENTER_UNUSED_LED: 0,           // Bottom LED on center strip (always off)
        CENTER_WIND_DIRECTION_LED: 19,  // Top LED on center strip (wind direction color)
        CENTER_WIND_SPEED_START: 1,     // First wind speed bar LED
        CENTER_WIND_SPEED_END: 18       // Last wind speed bar LED
    },

    // Update Intervals (milliseconds)
    INTERVALS: {
        LAMP_DATA_UPDATE: 780000,   // 13 minutes - matches Arduino poll rate
        BLINK_ANIMATION: 800,       // 0.8 seconds - threshold blink rate
        BROADCAST_CHECK: 300000,    // 5 minutes - check for admin broadcasts
        STATUS_MESSAGE_CLEAR: 3000  // 3 seconds - auto-clear success messages
    },

    // UI Timing
    TIMING: {
        MODAL_AUTO_CLOSE: 2000,         // 2 seconds - success modal auto-close
        STATUS_MESSAGE_DISPLAY: 3000,   // 3 seconds - status message duration
        ANIMATION_DURATION: 300         // 0.3 seconds - slide-in animations
    },

    // API Endpoints
    API: {
        UPDATE_LOCATION: '/update-location',
        UPDATE_THRESHOLD: '/update-threshold',
        UPDATE_WIND_THRESHOLD: '/update-wind-threshold',
        UPDATE_BRIGHTNESS: '/update-brightness',
        UPDATE_UNIT_PREFERENCE: '/update-unit-preference',
        UPDATE_OFF_TIMES: '/update-off-times',
        REPORT_ERROR: '/report-error',
        CHAT: '/api/chat',
        CHAT_STATUS: '/api/chat/status',
        BROADCASTS: '/api/broadcasts',
        ARDUINO_DATA: '/api/arduino/{id}/data'
    },

    // Canvas Drawing
    CANVAS: {
        WIDTH: 350,
        HEIGHT: 550,
        LED_VERTICAL_SPACING: 26,       // Pixels between LED rows
        SURFBOARD_BOTTOM_MARGIN: 30,    // Pixels from canvas bottom

        // Surfboard shape proportions
        SHAPE: {
            TAIL_WIDTH_START: 30,       // Narrowest point (bottom)
            TAIL_WIDTH_END: 60,         // After tail taper
            BODY_LOWER_WIDTH: 85,       // Lower body width
            BODY_MID_WIDTH: 85,         // Mid body (widest point)
            NOSE_WIDTH_START: 50,       // Before nose taper
            NOSE_WIDTH_END: 0           // Nose tip (pointed)
        }
    },

    // Wind Direction Colors (degrees → RGB)
    WIND_DIRECTION_COLORS: {
        0: [0, 255, 0],      // North - Green
        45: [128, 255, 0],   // Northeast - Yellow-Green
        90: [255, 255, 0],   // East - Yellow
        135: [255, 128, 0],  // Southeast - Orange
        180: [255, 0, 0],    // South - Red
        225: [128, 0, 255],  // Southwest - Purple
        270: [0, 0, 255],    // West - Blue
        315: [0, 255, 255]   // Northwest - Cyan
    },

    // Color Themes (matching Arduino themes)
    COLOR_THEMES: {
        ocean_breeze: {
            wave: [0, 150, 255],
            period: [0, 255, 200],
            wind: [255, 215, 0]  // Yellow
        },
        sunset_glow: {
            wave: [255, 100, 50],
            period: [255, 150, 0],
            wind: [255, 50, 100]
        },
        tropical_vibes: {
            wave: [0, 255, 150],
            period: [255, 200, 0],
            wind: [255, 100, 200]
        },
        day: { // Default theme
            wave: [0, 150, 255],
            period: [0, 255, 200],
            wind: [255, 215, 0] // Yellow
        }
    },

    // Form Validation Limits
    LIMITS: {
        WAVE_THRESHOLD_MIN_METERS: 0.0,
        WAVE_THRESHOLD_MAX_METERS: 3.0,
        WAVE_THRESHOLD_MIN_FEET: 0.0,
        WAVE_THRESHOLD_MAX_FEET: 10.0,

        WIND_THRESHOLD_MIN_KNOTS: 1,
        WIND_THRESHOLD_MAX_KNOTS: 40,
        WIND_THRESHOLD_MIN_MPH: 1,
        WIND_THRESHOLD_MAX_MPH: 46,

        ERROR_DESCRIPTION_MAX_LENGTH: 1000,
        CHAT_MESSAGE_MAX_LENGTH: 500
    },

    // Unit Conversions
    CONVERSIONS: {
        METERS_TO_FEET: 3.28084,
        KNOTS_TO_MPH: 1.15078,
        KNOTS_TO_MPS: 0.514444,     // 1 knot = 0.514444 m/s
        MPS_TO_MPH: 2.237           // 1 m/s = 2.237 mph
    },

    // LED Calculation Formulas (matching Arduino exactly)
    FORMULAS: {
        // Wave height: waveHeight_cm / 25 + 1
        WAVE_HEIGHT_DIVISOR: 25,
        WAVE_HEIGHT_OFFSET: 1,

        // Wind speed: windSpeed * 18.0 / 13.0
        WIND_SPEED_MULTIPLIER: 18.0,
        WIND_SPEED_DIVISOR: 13.0
    },

    // Visual Calibration Values (The "Enum")
    CALIBRATION: {
        STRIPS: {
            TOP_Y: 146,
            BOTTOM_Y: 440,
            LEFT_OFFSET_X: 31,
            RIGHT_OFFSET_X: 30,
            WIDTH: 6
        },
        LAYOUT: {
            LAMP_SCALE: 1.15,
            ARROW_TOP_Y: 82,     // px
            ARROW_SIZE: 69,      // px
            LEGEND_MARGIN_TOP: 30, // px
            LEGEND_SPREAD: 22    // px (padding left/right)
        }
    }
};

// Make config available globally
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DashboardConfig;
}
