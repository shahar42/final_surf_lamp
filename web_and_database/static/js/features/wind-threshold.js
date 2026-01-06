/**
 * Wind Threshold Range Feature
 * Handles wind speed threshold range slider with dual handles
 */

const WindThreshold = {
    slider: null,

    /**
     * Initialize wind threshold range slider
     */
    init: function() {
        const sliderElement = document.getElementById('windSlider');
        const updateBtn = document.getElementById('updateWindThreshold');
        const statusDiv = document.getElementById('wind-threshold-status');
        const minInput = document.getElementById('windThresholdMin');
        const maxInput = document.getElementById('windThresholdMax');
        const minLabel = document.getElementById('windMinLabel');
        const maxLabel = document.getElementById('windMaxLabel');

        if (!sliderElement || !updateBtn || !statusDiv || !minInput) {
            console.error('WindThreshold: Required elements not found');
            return;
        }

        // Get current values
        const currentMin = parseFloat(minInput.value) || 22;
        const currentMax = maxInput.value ? parseFloat(maxInput.value) : 50;

        // Slider range bounds (knots)
        const sliderMin = 1;
        const sliderMax = 50;

        // Create dual-handle range slider
        noUiSlider.create(sliderElement, {
            start: [currentMin, currentMax],
            connect: true,
            range: {
                'min': sliderMin,
                'max': sliderMax
            },
            step: 1,
            tooltips: false,
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

        // Update labels when slider changes
        this.slider.on('update', function(values, handle) {
            const min = values[0];
            const max = values[1];

            minLabel.textContent = `${min} knots`;
            maxLabel.textContent = `${max} knots`;

            // Store values in hidden inputs
            minInput.value = min;
            maxInput.value = max;
        });

        // Handle "Set" button click
        updateBtn.addEventListener('click', async () => {
            const values = this.slider.get();
            const thresholdMin = parseInt(values[0]);
            const thresholdMax = parseInt(values[1]);

            StatusMessage.loading(statusDiv);

            // Make API request
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
        });
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.WindThreshold = WindThreshold;
}
