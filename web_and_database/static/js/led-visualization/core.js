/**
 * LED Visualization Core
 * Canvas drawing functions for surfboard LED visualization
 */

const LEDVisualizationCore = {
    /**
     * Draw a liquid-style LED strip line with wave effect on top
     * @param {CanvasRenderingContext2D} ctx - Canvas context
     * @param {number} x - X position of the strip center
     * @param {number} yBottom - Y position of the bottom of the strip
     * @param {number} yTopMax - Y position of the top of the strip (100% full)
     * @param {number} width - Width of the strip in pixels
     * @param {number} fillPercentage - 0.0 to 1.0
     * @param {Array<number>} color - RGB color array [r, g, b]
     * @param {number} time - Animation time variable
     */
    drawLiquidStrip: function(ctx, x, yBottom, yTopMax, width, fillPercentage, color, time) {
        if (fillPercentage <= 0.01) return;

        // Calculate current height based on fill percentage
        const totalHeight = yBottom - yTopMax;
        const currentHeight = totalHeight * fillPercentage;
        const ySurface = yBottom - currentHeight;

        // Set styles
        const rgbString = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
        const rgbaGlow = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.6)`;
        
        ctx.fillStyle = rgbString;
        ctx.strokeStyle = rgbString;
        
        // Save context for clipping/effects
        ctx.save();

        // 1. Draw Glow (Behind)
        ctx.shadowBlur = 15;
        ctx.shadowColor = rgbaGlow;
        
        // 2. Draw the Main Liquid Shape
        ctx.beginPath();
        ctx.moveTo(x - width/2, yBottom); // Start bottom-left

        // Draw up the left side
        ctx.lineTo(x - width/2, ySurface);

        // Draw the wavy top surface
        // We use small segments to create the sine wave
        const segments = 10;
        const step = width / segments;
        
        for (let i = 0; i <= segments; i++) {
            const currentX = (x - width/2) + (i * step);
            
            // Wave Physics parameters
            // Amplitude decreases as fill gets very low (so empty strips don't wave crazily)
            const amplitude = 2.5 * Math.min(1.0, fillPercentage * 5); 
            const frequency = 0.5;
            const phase = time + (x * 0.1); // Offset phase by x position so strips don't wave in unison

            // Calculate Y offset (sine wave)
            const waveY = Math.sin((i + phase) * frequency) * amplitude;
            
            ctx.lineTo(currentX, ySurface + waveY);
        }

        // Draw down the right side
        ctx.lineTo(x + width/2, yBottom);
        
        // Close shape at bottom
        ctx.closePath();
        
        // Fill the shape
        ctx.fill();

        // 3. Add internal "shine" (highlight) to make it look like a glass tube
        // Gradient from left to right: transparent -> whiteish -> transparent
        const shineGradient = ctx.createLinearGradient(x - width/2, ySurface, x + width/2, ySurface);
        shineGradient.addColorStop(0, 'rgba(255,255,255,0)');
        shineGradient.addColorStop(0.5, 'rgba(255,255,255,0.4)');
        shineGradient.addColorStop(1, 'rgba(255,255,255,0)');
        
        ctx.fillStyle = shineGradient;
        ctx.fill(); // Fill over the existing shape

        ctx.restore();
    },

    /**
     * Draw the wind direction indicator (top nose LED)
     */
    drawWindDirectionIndicator: function(ctx, x, y, color) {
        ctx.save();
        const radius = 6;
        
        // Glow
        ctx.shadowBlur = 10;
        ctx.shadowColor = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.8)`;
        
        ctx.fillStyle = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
        
        // Highlight
        ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
        ctx.beginPath();
        ctx.arc(x - 2, y - 2, 2, 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();
    },

    /**
     * Draw the complete surfboard with image background and liquid LED strips
     * @param {CanvasRenderingContext2D} ctx - Canvas context
     * @param {HTMLCanvasElement} canvas - Canvas element
     * @param {number} leftFill - 0.0-1.0 fill for left strip (period)
     * @param {number} centerFill - 0.0-1.0 fill for center strip (wind speed)
     * @param {number} rightFill - 0.0-1.0 fill for right strip (wave height)
     * @param {object} theme - Theme colors {wave, period, wind}
     * @param {Array<number>} windDirColor - RGB color for wind direction LED
     * @param {HTMLImageElement} image - Loaded surfboard image
     * @param {number} time - Animation time
     */
    drawSurfboard: function(ctx, canvas, leftFill, centerFill, rightFill, theme, windDirColor, image, time) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // 1. Draw Background Image
        if (image) {
            // Draw image centered and covering most of the canvas
            // Canvas is 350x550.
            // We want to preserve aspect ratio. 
            // Assume image is vertical.
            const padding = 20;
            const targetHeight = canvas.height - (padding * 2);
            const scale = targetHeight / image.height;
            const targetWidth = image.width * scale;
            const x = (canvas.width - targetWidth) / 2;
            const y = padding;

            ctx.drawImage(image, x, y, targetWidth, targetHeight);
        } else {
            // Fallback if image not loaded yet (simple grey shape)
            ctx.fillStyle = '#333';
            ctx.beginPath();
            ctx.ellipse(canvas.width/2, canvas.height/2, 60, 240, 0, 0, Math.PI*2);
            ctx.fill();
        }

        // 2. Define Strip Positions (Calibrated for standard surf lamp shape)
        // These are approximations since we can't see the new image.
        // Center of canvas is 175.
        const centerX = canvas.width / 2;
        const bottomY = canvas.height - 60; // Start slightly above bottom
        const topY = 80; // End below top
        
        const stripWidth = 12; 
        const sideOffset = 55; // Distance of side strips from center

        // LEFT RAIL: Wave Period
        if (theme && theme.period) {
            this.drawLiquidStrip(
                ctx, 
                centerX - sideOffset, // x
                bottomY, // yBottom
                topY + 40, // yTop (side strips are shorter)
                stripWidth,
                leftFill || 0,
                theme.period,
                time
            );
        }

        // CENTER STRIP: Wind Speed
        if (theme && theme.wind) {
            // Center strip starts a bit higher (above the tail block)
            this.drawLiquidStrip(
                ctx,
                centerX,
                bottomY - 20, 
                topY + 30, // Leaves room for wind direction LED at top
                stripWidth,
                centerFill || 0,
                theme.wind,
                time
            );
        }

        // RIGHT RAIL: Wave Height
        if (theme && theme.wave) {
            this.drawLiquidStrip(
                ctx,
                centerX + sideOffset,
                bottomY,
                topY + 40,
                stripWidth,
                rightFill || 0,
                theme.wave,
                time
            );
        }

        // 3. Draw Wind Direction LED (Nose)
        // This is a single dot at the very top of the center strip
        if (windDirColor) {
            this.drawWindDirectionIndicator(
                ctx, 
                centerX, 
                topY + 15, // Just above the wind speed strip
                windDirColor
            );
        }
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.LEDVisualizationCore = LEDVisualizationCore;
}

// Make globally available
if (typeof window !== 'undefined') {
    window.LEDVisualizationCore = LEDVisualizationCore;
}
