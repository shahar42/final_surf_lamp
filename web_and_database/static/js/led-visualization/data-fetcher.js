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
    fetchInterval: null,
    lampImage: null,
    imageLoaded: false,
    animationFrameId: null,
    time: 0,
    cachedData: null, // Store data for animation loop

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

        // Load the surfboard image
        this.lampImage = new Image();
        this.lampImage.src = '/static/annimaiton_lamp.png'; // Note: User provided filename typo
        this.lampImage.onload = () => {
            this.imageLoaded = true;
            // Force a redraw once loaded if we have data
            if (this.cachedData) {
                this.updateLEDVisualization(this.cachedData);
            }
        };

        // Initial fetch
        this.fetchLampData();

        // Start update interval (13 minutes)
        this.fetchInterval = setInterval(
            () => this.fetchLampData(),
            DashboardConfig.INTERVALS.LAMP_DATA_UPDATE
        );

        // Start Animation Loop (for liquid effects)
        this.animate();
    },

    /**
     * Animation Loop
     */
    animate: function() {
        this.time += 0.05; // Increment time for wave physics
        
        if (this.cachedData) {
            this.updateLEDVisualization(this.cachedData);
        } else if (this.imageLoaded) {
            // If no data yet but image loaded, just draw the board
            LEDVisualizationCore.drawSurfboard(
                this.ctx, this.canvas, 
                0, 0, 0, 
                ThemeManager.getTheme(this.currentTheme), 
                null, 
                this.lampImage, 
                this.time
            );
        }

        this.animationFrameId = requestAnimationFrame(() => this.animate());
    },

    /**
     * Update LED visualization from lamp data
     * @param {object} data - Lamp data object with wave/wind conditions
     */
    updateLEDVisualization: function(data) {
        this.cachedData = data; // Cache for animation loop
        const theme = ThemeManager.getTheme(this.currentTheme);

        // Calculate Fill Percentages (0.0 to 1.0)
        // We use the same formulas but normalize them to a 0-1 range for the liquid fill

        // Wave height (Right Strip)
        // Max 15 LEDs roughly corresponds to max reasonable wave height (~3m)
        // Formula: height_cm / 25 + 1. Max is 15.
        // We calculate raw "led count" then divide by max to get percentage.
        const rawWaveLeds = Math.max(0, (data.wave_height_cm / DashboardConfig.FORMULAS.WAVE_HEIGHT_DIVISOR) + DashboardConfig.FORMULAS.WAVE_HEIGHT_OFFSET);
        const waveFill = Math.min(1.0, rawWaveLeds / DashboardConfig.LED.NUM_LEDS_RIGHT);

        // Wave period (Left Strip)
        // Max 15 seconds typically covers most swells.
        const rawPeriodLeds = Math.max(0, data.wave_period_s);
        const periodFill = Math.min(1.0, rawPeriodLeds / DashboardConfig.LED.NUM_LEDS_LEFT);

        // Wind speed (Center Strip)
        // Max 18 LEDs. Formula: speed * 18 / 13.
        const rawWindLeds = Math.max(0, (data.wind_speed_mps * DashboardConfig.FORMULAS.WIND_SPEED_MULTIPLIER / DashboardConfig.FORMULAS.WIND_SPEED_DIVISOR));
        // Center strip effectively has 18 usable LEDs for speed (indices 1-18)
        const windFill = Math.min(1.0, rawWindLeds / (DashboardConfig.LED.NUM_LEDS_CENTER - 2));

        // Get wind direction color for nose LED
        const windDirColor = ThemeManager.getWindDirectionColor(data.wind_direction_deg);

        // Draw surfboard with Liquid Data
        LEDVisualizationCore.drawSurfboard(
            this.ctx,
            this.canvas,
            periodFill,
            windFill,
            waveFill,
            theme,
            windDirColor,
            this.imageLoaded ? this.lampImage : null,
            this.time
        );

        // Update wind direction arrow (HTML overlay)
        // Add 180° to show where wind is GOING, not where it's coming from
        const windArrow = document.getElementById('windArrow');
        if (windArrow && data.wind_direction_deg !== null) {
            windArrow.style.transform = `rotate(${data.wind_direction_deg + 180}deg)`;
        }

        // Update last update time text
        const timestamp = data.last_updated.endsWith('Z') ? data.last_updated : data.last_updated + 'Z';
        const lastUpdate = new Date(timestamp);
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
                    // Update cache, the animate loop will handle the drawing
                    this.cachedData = data;
                } else {
                    console.log('No lamp data available yet');
                }
            })
            .catch(error => {
                console.error('Error fetching lamp data:', error);
            });
    },

    /**
     * Stop all intervals (cleanup)
     */
    destroy: function() {
        if (this.fetchInterval) {
            clearInterval(this.fetchInterval);
            this.fetchInterval = null;
        }
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.LEDDataFetcher = LEDDataFetcher;
}
