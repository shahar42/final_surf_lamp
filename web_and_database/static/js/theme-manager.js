/**
 * Theme Manager
 * Handles color themes and wind direction colors for LED visualization
 */

const ThemeManager = {
    /**
     * Get theme colors by name
     * @param {string} themeName - Theme name (ocean_breeze, sunset_glow, etc.)
     * @returns {object} Theme colors {wave, period, wind}
     */
    getTheme: function(themeName) {
        const theme = DashboardConfig.COLOR_THEMES[themeName];

        if (!theme) {
            console.warn(`Theme "${themeName}" not found, using default`);
            return DashboardConfig.COLOR_THEMES.day;
        }

        return theme;
    },

    /**
     * Get wind direction color based on degrees
     * @param {number} degrees - Wind direction in degrees (0-360)
     * @returns {Array<number>} RGB color array [r, g, b]
     */
    getWindDirectionColor: function(degrees) {
        const directions = Object.keys(DashboardConfig.WIND_DIRECTION_COLORS).map(Number);

        // Find closest direction
        let closest = directions[0];
        let minDiff = Math.abs(degrees - closest);

        for (let dir of directions) {
            const diff = Math.abs(degrees - dir);
            if (diff < minDiff) {
                minDiff = diff;
                closest = dir;
            }
        }

        return DashboardConfig.WIND_DIRECTION_COLORS[closest];
    },

    /**
     * Get human-readable direction name from degrees
     * @param {number} degrees - Wind direction in degrees (0-360)
     * @returns {string} Direction name (N, NE, E, etc.)
     */
    getWindDirectionName: function(degrees) {
        const directions = {
            0: 'N',
            45: 'NE',
            90: 'E',
            135: 'SE',
            180: 'S',
            225: 'SW',
            270: 'W',
            315: 'NW'
        };

        // Find closest direction
        const directionDegrees = Object.keys(directions).map(Number);
        let closest = directionDegrees[0];
        let minDiff = Math.abs(degrees - closest);

        for (let dir of directionDegrees) {
            const diff = Math.abs(degrees - dir);
            if (diff < minDiff) {
                minDiff = diff;
                closest = dir;
            }
        }

        return directions[closest];
    },

    /**
     * Convert RGB array to CSS rgb() string
     * @param {Array<number>} rgb - RGB array [r, g, b]
     * @returns {string} CSS rgb string "rgb(r, g, b)"
     */
    rgbToString: function(rgb) {
        return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
    },

    /**
     * Convert RGB array to CSS rgba() string with alpha
     * @param {Array<number>} rgb - RGB array [r, g, b]
     * @param {number} alpha - Alpha value (0-1)
     * @returns {string} CSS rgba string "rgba(r, g, b, a)"
     */
    rgbToRgba: function(rgb, alpha) {
        return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;
    },

    /**
     * Get all available theme names
     * @returns {Array<string>} Array of theme names
     */
    getAvailableThemes: function() {
        return Object.keys(DashboardConfig.COLOR_THEMES);
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.ThemeManager = ThemeManager;
}
