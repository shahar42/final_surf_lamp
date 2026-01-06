/**
 * Wave Threshold Range Feature
 * Handles wave height threshold range slider with dual handles
 */

const WaveThreshold = {
    slider: null,
    updateTimeout: null,

    /**
     * Initialize wave threshold range slider
     */
    init: function() {
        const sliderElement = document.getElementById('waveSlider');
        const statusDiv = document.getElementById('threshold-status');
        const minInput = document.getElementById('waveThresholdMin');
        const maxInput = document.getElementById('waveThresholdMax');

        if (!sliderElement || !statusDiv || !minInput) {
            console.error('WaveThreshold: Required elements not found');
            return;
        }

        const unit = minInput.dataset.unit;
        const isFeet = unit === 'feet';
        const unitLabel = isFeet ? 'ft' : 'm';

        // Get current values
        const currentMin = parseFloat(minInput.value) || (isFeet ? 3.28 : 1.0);
        const currentMax = maxInput.value ? parseFloat(maxInput.value) : (isFeet ? 32.8 : 10.0);

        // Slider range bounds
        const sliderMin = isFeet ? 0.3 : 0.1;
        const sliderMax = isFeet ? 33 : 10.0;

        // Create dual-handle range slider
        noUiSlider.create(sliderElement, {
            start: [currentMin, currentMax],
            connect: true,
            range: {
                'min': sliderMin,
                'max': sliderMax
            },
            step: isFeet ? 0.3 : 0.1,
            tooltips: [true, true],  // Show tooltips above both handles
            format: {
                to: function(value) {
                    return parseFloat(value.toFixed(1));
                },
                from: function(value) {
                    return parseFloat(value);
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
            const thresholdMin = parseFloat(values[0]);
            const thresholdMax = parseFloat(values[1]);

            // Convert to meters if user prefers feet
            const thresholdMinMeters = isFeet ? thresholdMin / DashboardConfig.CONVERSIONS.METERS_TO_FEET : thresholdMin;
            const thresholdMaxMeters = isFeet ? thresholdMax / DashboardConfig.CONVERSIONS.METERS_TO_FEET : thresholdMax;

            // Debounce: clear previous timeout
            if (this.updateTimeout) {
                clearTimeout(this.updateTimeout);
            }

            // Wait 300ms before sending API request
            this.updateTimeout = setTimeout(async () => {
                StatusMessage.loading(statusDiv);

                const result = await ApiClient.post(
                    DashboardConfig.API.UPDATE_THRESHOLD,
                    {
                        threshold_min: thresholdMinMeters,
                        threshold_max: thresholdMaxMeters
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
    window.WaveThreshold = WaveThreshold;
}
