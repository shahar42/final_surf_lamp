/**
 * Wind Threshold Range Feature
 * Handles wind speed threshold range slider with dual handles
 */

const WindThreshold = {
    slider: null,
    updateTimeout: null,

    /**
     * Initialize wind threshold range slider
     */
    init: function() {
        const sliderElement = document.getElementById('windSlider');
        const statusDiv = document.getElementById('wind-threshold-status');
        const minInput = document.getElementById('windThresholdMin');
        const maxInput = document.getElementById('windThresholdMax');

        if (!sliderElement || !statusDiv || !minInput) {
            console.error('WindThreshold: Required elements not found');
            return;
        }

        // Get current values
        const currentMin = parseFloat(minInput.value) || DashboardConfig.LIMITS.WIND_THRESHOLD_MIN_KNOTS;
        const currentMax = maxInput.value ? parseFloat(maxInput.value) : DashboardConfig.LIMITS.WIND_THRESHOLD_MAX_KNOTS;

        console.log('[WIND SLIDER DEBUG] minInput.value:', minInput.value, 'maxInput.value:', maxInput.value);
        console.log('[WIND SLIDER DEBUG] Parsed - currentMin:', currentMin, 'currentMax:', currentMax);

        // Slider range bounds (knots)
        const sliderMin = DashboardConfig.LIMITS.WIND_THRESHOLD_MIN_KNOTS;
        const sliderMax = DashboardConfig.LIMITS.WIND_THRESHOLD_MAX_KNOTS;

        // Create dual-handle range slider
        noUiSlider.create(sliderElement, {
            start: [currentMin, currentMax],
            connect: true,
            range: {
                'min': sliderMin,
                'max': sliderMax
            },
            step: 1,
            tooltips: [true, true],  // Show tooltips above both handles
            format: {
                to: function(value) {
                    return Math.round(value);
                },
                from: function(value) {
                    return parseInt(value);
                }
            }
        });

        this.slider = sliderElement.noUiSlider;

        // Store values in hidden inputs when slider changes
        this.slider.on('update', function(values, handle) {
            minInput.value = values[0];
            maxInput.value = values[1];
        });

        // Auto-update on slider change (when user releases handle)
        this.slider.on('change', async (values, handle) => {
            const thresholdMin = parseInt(values[0]);
            const thresholdMax = parseInt(values[1]);

            // Debounce: clear previous timeout
            if (this.updateTimeout) {
                clearTimeout(this.updateTimeout);
            }

            // Wait 300ms before sending API request
            this.updateTimeout = setTimeout(async () => {
                StatusMessage.loading(statusDiv);

                const result = await ApiClient.post(
                    DashboardConfig.API.UPDATE_WIND_THRESHOLD,
                    {
                        threshold_min: thresholdMin,
                        threshold_max: thresholdMax
                    }
                );

                if (result.ok) {
                    StatusMessage.success(statusDiv, result.data.message);
                } else {
                    StatusMessage.error(statusDiv, 'Error: ' + result.data.message);
                }
            }, 300);
        });
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.WindThreshold = WindThreshold;
}
