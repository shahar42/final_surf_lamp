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

        // Get Style Config
        // Check if window.styleCalibration exists (live tuning), otherwise use Config
        const style = (typeof window !== 'undefined' && window.styleCalibration) ? window.styleCalibration : DashboardConfig.CALIBRATION.STYLE;

        // Calculate current height
        const totalHeight = yBottom - yTopMax;
        const currentHeight = totalHeight * fillPercentage;
        const ySurface = yBottom - currentHeight;

        const rgbString = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
        const rgbaGlow = `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${style.GLOW_OPACITY})`;
        
        ctx.save();

        // 1. Draw "Groove" Shadow (The hole in the wood) - Behind the light
        // We use 'multiply' to darken the wood texture
        ctx.globalCompositeOperation = 'multiply';
        ctx.fillStyle = `rgba(0,0,0,${style.GROOVE_SHADOW_OPACITY})`;
        ctx.shadowBlur = 5;
        ctx.shadowColor = 'rgba(0,0,0,0.5)';
        
        // Draw the full strip length as a groove (optional: or just the filled part? 
        // Realistically the groove exists even if empty, but for this visual we stick to the fill)
        this.drawStripPath(ctx, x, yBottom, ySurface, width, time);
        ctx.fill();

        // 2. Draw the Light (Screen/Overlay blend for glow)
        ctx.globalCompositeOperation = 'screen'; 
        ctx.shadowBlur = style.GLOW_BLUR;
        ctx.shadowColor = rgbaGlow;
        ctx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${style.STRIP_OPACITY})`;
        
        this.drawStripPath(ctx, x, yBottom, ySurface, width, time);
        ctx.fill();

        // 3. Inner Shine (Glass/Acrylic highlight)
        ctx.globalCompositeOperation = 'source-over'; // Reset blend for white shine
        ctx.shadowBlur = 0;
        const shineGradient = ctx.createLinearGradient(x - width/2, ySurface, x + width/2, ySurface);
        shineGradient.addColorStop(0, 'rgba(255,255,255,0)');
        shineGradient.addColorStop(0.5, `rgba(255,255,255,${style.INNER_SHINE_ALPHA})`);
        shineGradient.addColorStop(1, 'rgba(255,255,255,0)');
        
        ctx.fillStyle = shineGradient;
        this.drawStripPath(ctx, x, yBottom, ySurface, width, time);
        ctx.fill();

        ctx.restore();
    },

    // Helper to draw the wavy path
    drawStripPath: function(ctx, x, yBottom, ySurface, width, time) {
        ctx.beginPath();
        ctx.moveTo(x - width/2, yBottom);
        ctx.lineTo(x - width/2, ySurface);

        const segments = 10;
        const step = width / segments;
        for (let i = 0; i <= segments; i++) {
            const currentX = (x - width/2) + (i * step);
            const amplitude = 2.5 * Math.min(1.0, (yBottom - ySurface) / 50); 
            const frequency = 0.5;
            const phase = time + (x * 0.1);
            const waveY = Math.sin((i + phase) * frequency) * amplitude;
            ctx.lineTo(currentX, ySurface + waveY);
        }

        ctx.lineTo(x + width/2, yBottom);
        ctx.closePath();
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
            const padding = 20;
            const targetHeight = canvas.height - (padding * 2);
            const scale = targetHeight / image.height;
            const targetWidth = image.width * scale;
            const x = (canvas.width - targetWidth) / 2;
            const y = padding;

            ctx.drawImage(image, x, y, targetWidth, targetHeight);
        } else {
            ctx.fillStyle = '#333';
            ctx.beginPath();
            ctx.ellipse(canvas.width/2, canvas.height/2, 60, 240, 0, 0, Math.PI*2);
            ctx.fill();
        }

        // 2. Define Strip Positions
        // Using centralized calibration from config.js
        const centerX = canvas.width / 2;
        const cal = DashboardConfig.CALIBRATION.STRIPS;
        
        const bottomY = cal.BOTTOM_Y;
        const topY = cal.TOP_Y;
        const stripWidth = cal.WIDTH;
        
        const leftOffset = cal.LEFT_OFFSET_X;
        const rightOffset = cal.RIGHT_OFFSET_X;

        // LEFT RAIL: Wave Period
        if (theme && theme.period) {
            this.drawLiquidStrip(
                ctx, 
                centerX - leftOffset, 
                bottomY, 
                topY, // Uniform top
                stripWidth,
                leftFill || 0,
                theme.period,
                time
            );
        }

        // CENTER STRIP: Wind Speed
        if (theme && theme.wind) {
            this.drawLiquidStrip(
                ctx,
                centerX,
                bottomY, // Uniform bottom
                topY, // Uniform top
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
                centerX + rightOffset,
                bottomY,
                topY, // Uniform top
                stripWidth,
                rightFill || 0,
                theme.wave,
                time
            );
        }

        // Note: Wind direction is handled by the HTML arrow overlay in dashboard.html
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.LEDVisualizationCore = LEDVisualizationCore;
}
