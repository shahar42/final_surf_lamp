/**
 * LED Data Fetcher
 * Handles fetching lamp data and updating LED visualization
 */

const LEDDataFetcher = {
    // State
    canvas: null,
    ctx: null,
    arduinoId: null,
    currentTheme: 'ocean_breeze',
    isBlinking: false,
    blinkState: true,
    fetchInterval: null,
    blinkInterval: null,

    /**
     * Initialize LED data fetcher
     * @param {number} arduinoId - Arduino ID to fetch data for
     * @param {string} themeName - Current theme name
     */
    init: function(arduinoId, themeName) {
        this.arduinoId = arduinoId;
        this.currentTheme = themeName || 'ocean_breeze';

        // Get canvas and context
        this.canvas = document.getElementById('surfboardCanvas');
        if (!this.canvas) {
            console.error('Canvas element not found');
            return;
        }

        this.ctx = this.canvas.getContext('2d');

        // Apply canvas styling
        this.canvas.classList.add('led-strip-canvas');

        // Initial fetch
        this.fetchLampData();

        // Start update interval (13 minutes)
        this.fetchInterval = setInterval(
            () => this.fetchLampData(),
            DashboardConfig.INTERVALS.LAMP_DATA_UPDATE
        );

        // Start blink animation (0.8s intervals)
        this.blinkInterval = setInterval(
            () => this.blinkLoop(),
            DashboardConfig.INTERVALS.BLINK_ANIMATION
        );
    },

    /**
     * Update LED visualization from lamp data
     * @param {object} data - Lamp data object with wave/wind conditions
     */
    updateLEDVisualization: function(data) {
        const theme = ThemeManager.getTheme(this.currentTheme);

        // Calculate LED counts matching Arduino formulas EXACTLY
        // Wave height: waveHeight_cm / 25 + 1 (Arduino line 829, max 15 LEDs)
        const waveLEDCount = Math.max(0, Math.min(
            DashboardConfig.LED.NUM_LEDS_RIGHT,
            Math.floor(data.wave_height_cm / DashboardConfig.FORMULAS.WAVE_HEIGHT_DIVISOR) +
            DashboardConfig.FORMULAS.WAVE_HEIGHT_OFFSET
        ));

        // Wave period: Direct value (Arduino line 830, max 15 LEDs)
        const periodLEDCount = Math.max(0, Math.min(
            DashboardConfig.LED.NUM_LEDS_LEFT,
            Math.floor(data.wave_period_s)
        ));

        // Wind speed: windSpeed * 18.0 / 13.0 (Arduino line 828, max 18 LEDs, constrain 1 to NUM_LEDS_CENTER-2)
        // Note: Wind speed LEDs are 1-18, so we return the count that includes LED 1
        const windLEDCount = Math.max(1, Math.min(
            DashboardConfig.LED.NUM_LEDS_CENTER - 2,
            Math.floor(
                data.wind_speed_mps *
                DashboardConfig.FORMULAS.WIND_SPEED_MULTIPLIER /
                DashboardConfig.FORMULAS.WIND_SPEED_DIVISOR
            )
        ));

        // Get wind direction color for nose LED
        const windDirColor = ThemeManager.getWindDirectionColor(data.wind_direction_deg);

        // Check threshold alerts
        const waveThresholdExceeded = data.wave_height_cm > data.wave_threshold_cm;
        const windThresholdExceeded = data.wind_speed_mps > (data.wind_speed_threshold_knots * DashboardConfig.CONVERSIONS.KNOTS_TO_MPS);

        this.isBlinking = waveThresholdExceeded || windThresholdExceeded;

        // Draw surfboard with LED data
        // Left rail = period, Center = WIND speed, Right rail = wave height
        LEDVisualizationCore.drawSurfboard(
            this.ctx,
            this.canvas,
            periodLEDCount,
            windLEDCount,
            waveLEDCount,
            theme,
            windDirColor,
            this.isBlinking,
            this.blinkState
        );

        // Update last update time
        const lastUpdate = new Date(data.last_updated);
        const now = new Date();
        const diffMinutes = Math.floor((now - lastUpdate) / 1000 / 60);
        const lastUpdateEl = document.getElementById('lastUpdateTime');
        if (lastUpdateEl) {
            lastUpdateEl.textContent = diffMinutes < 1 ? 'just now' : `${diffMinutes} min ago`;
        }
    },

    /**
     * Fetch lamp data from API
     */
    fetchLampData: function() {
        const url = DashboardConfig.API.ARDUINO_DATA.replace('{id}', this.arduinoId);

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.data_available) {
                    this.updateLEDVisualization(data);
                } else {
                    console.log('No lamp data available yet');
                }
            })
            .catch(error => {
                console.error('Error fetching lamp data:', error);
            });
    },

    /**
     * Blink animation loop
     */
    blinkLoop: function() {
        if (this.isBlinking) {
            this.blinkState = !this.blinkState;
        } else {
            this.blinkState = true;
        }
        // Note: The next fetchLampData() will redraw with current blink state
        // We don't redraw immediately to avoid excessive redraws
    },

    /**
     * Stop all intervals (cleanup)
     */
    destroy: function() {
        if (this.fetchInterval) {
            clearInterval(this.fetchInterval);
            this.fetchInterval = null;
        }
        if (this.blinkInterval) {
            clearInterval(this.blinkInterval);
            this.blinkInterval = null;
        }
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.LEDDataFetcher = LEDDataFetcher;
}
