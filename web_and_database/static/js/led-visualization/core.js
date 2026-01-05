/**
 * LED Visualization Core
 * Canvas drawing functions for surfboard LED visualization
 */

const LEDVisualizationCore = {
    /**
     * Draw a single LED on the canvas
     * @param {CanvasRenderingContext2D} ctx - Canvas context
     * @param {number} x - X position
     * @param {number} y - Y position
     * @param {Array<number>} color - RGB color array [r, g, b]
     * @param {boolean} isLit - Whether LED is illuminated
     * @param {boolean} glow - Whether to draw glow effect (default: true)
     */
    drawLED: function(ctx, x, y, color, isLit, glow = true) {
        const radius = DashboardConfig.LED.LED_RADIUS;

        if (!isLit) {
            // Dim LED (off state)
            ctx.fillStyle = 'rgba(50, 50, 50, 0.3)';
            ctx.beginPath();
            ctx.arc(x, y, radius, 0, Math.PI * 2);
            ctx.fill();
            return;
        }

        // Draw glow effect
        if (glow) {
            const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius * 2);
            gradient.addColorStop(0, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.8)`);
            gradient.addColorStop(0.5, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.4)`);
            gradient.addColorStop(1, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0)`);
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(x, y, radius * 2, 0, Math.PI * 2);
            ctx.fill();
        }

        // Draw LED core
        ctx.fillStyle = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();

        // Add bright center highlight
        const highlightGradient = ctx.createRadialGradient(x - 5, y - 5, 0, x, y, radius);
        highlightGradient.addColorStop(0, 'rgba(255, 255, 255, 0.8)');
        highlightGradient.addColorStop(0.5, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.5)`);
        highlightGradient.addColorStop(1, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0)`);
        ctx.fillStyle = highlightGradient;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
    },

    /**
     * Calculate surfboard LED positions
     * Matches Arduino hardware layout (20 center, 15 left, 15 right)
     * @param {HTMLCanvasElement} canvas - Canvas element
     * @returns {Array<object>} Array of position objects {left, center, right}
     */
    getSurfboardLEDPositions: function(canvas) {
        const width = canvas.width;
        const height = canvas.height;
        const centerX = width / 2;
        const spacing = DashboardConfig.CANVAS.LED_VERTICAL_SPACING;
        const bottomMargin = DashboardConfig.CANVAS.SURFBOARD_BOTTOM_MARGIN;
        const NUM_LEDS_CENTER = DashboardConfig.LED.NUM_LEDS_CENTER;
        const NUM_LEDS_LEFT = DashboardConfig.LED.NUM_LEDS_LEFT;
        const NUM_LEDS_RIGHT = DashboardConfig.LED.NUM_LEDS_RIGHT;

        const positions = [];

        // Generate 20 rows for center strip (max LED count)
        for (let i = 0; i < NUM_LEDS_CENTER; i++) {
            const y = height - bottomMargin - (i * spacing); // Bottom to top

            // Calculate surfboard width at this position (classic surfboard shape)
            let widthAtPosition;
            const normalizedPos = i / (NUM_LEDS_CENTER - 1); // 0 to 1

            if (normalizedPos < 0.2) {
                // Tail (narrow) - LEDs 0-3
                widthAtPosition = 30 + (normalizedPos / 0.2) * 30;
            } else if (normalizedPos < 0.4) {
                // Lower body (widening) - LEDs 4-7
                widthAtPosition = 60 + ((normalizedPos - 0.2) / 0.2) * 25;
            } else if (normalizedPos < 0.7) {
                // Mid body (widest point) - LEDs 8-13
                widthAtPosition = 85;
            } else if (normalizedPos < 0.85) {
                // Upper body (tapering) - LEDs 14-16
                widthAtPosition = 85 - ((normalizedPos - 0.7) / 0.15) * 35;
            } else {
                // Nose (sharp taper) - LEDs 17-19
                widthAtPosition = 50 - ((normalizedPos - 0.85) / 0.15) * 50;
            }

            const row = {
                // Left strip (wave period) - only 15 LEDs
                left: i < NUM_LEDS_LEFT ? {x: centerX - widthAtPosition, y: y} : null,
                // Center strip (wind speed) - all 20 LEDs
                center: {x: centerX, y: y},
                // Right strip (wave height) - only 15 LEDs
                right: i < NUM_LEDS_RIGHT ? {x: centerX + widthAtPosition, y: y} : null
            };

            positions.push(row);
        }

        return positions;
    },

    /**
     * Draw the complete surfboard with all LED strips
     * @param {CanvasRenderingContext2D} ctx - Canvas context
     * @param {HTMLCanvasElement} canvas - Canvas element
     * @param {number} leftLEDCount - Number of lit LEDs on left strip (period)
     * @param {number} centerLEDCount - Number of lit LEDs on center strip (wind speed)
     * @param {number} rightLEDCount - Number of lit LEDs on right strip (wave height)
     * @param {object} theme - Theme colors {wave, period, wind}
     * @param {Array<number>} windDirColor - RGB color for wind direction LED
     * @param {boolean} blink - Whether blinking is active
     * @param {boolean} blinkState - Current blink state (visible/hidden)
     */
    drawSurfboard: function(ctx, canvas, leftLEDCount, centerLEDCount, rightLEDCount, theme, windDirColor, blink, blinkState) {
        const NUM_LEDS_CENTER = DashboardConfig.LED.NUM_LEDS_CENTER;
        const CENTER_WIND_DIRECTION_LED = DashboardConfig.LED.CENTER_WIND_DIRECTION_LED;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const positions = this.getSurfboardLEDPositions(canvas);

        // Draw each row of LEDs
        for (let i = 0; i < NUM_LEDS_CENTER; i++) {
            const row = positions[i];

            // Apply blinking effect if threshold exceeded
            const shouldBlink = blink && !blinkState;

            // LEFT RAIL: Wave period (15 LEDs, 0-14)
            if (row.left) {
                const leftLit = (i < leftLEDCount);
                this.drawLED(ctx, row.left.x, row.left.y, theme.period, leftLit && !shouldBlink);
            }

            // CENTER STRIP: Wind speed (20 LEDs)
            // LED 0 = unused (off)
            // LEDs 1-18 = wind speed bars
            // LED 19 = wind direction indicator (always on with direction color)
            if (row.center) {
                const isWindDirection = (i === CENTER_WIND_DIRECTION_LED); // LED 19 = top
                const isLED0 = (i === 0); // Bottom LED unused

                if (isWindDirection) {
                    // LED 19: Skip - replaced by arrow compass
                    continue;
                } else if (isLED0) {
                    // LED 0: Always off
                    this.drawLED(ctx, row.center.x, row.center.y, theme.wind, false);
                } else {
                    // LEDs 1-18: Wind speed bars (centerLEDCount already accounts for LED 1 start)
                    const centerLit = (i <= centerLEDCount); // i=1 is first bar, i=2 is second, etc.
                    this.drawLED(ctx, row.center.x, row.center.y, theme.wind, centerLit && !shouldBlink);
                }
            }

            // RIGHT RAIL: Wave height (15 LEDs, 0-14)
            if (row.right) {
                const rightLit = (i < rightLEDCount);
                this.drawLED(ctx, row.right.x, row.right.y, theme.wave, rightLit && !shouldBlink);
            }
        }
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.LEDVisualizationCore = LEDVisualizationCore;
}
