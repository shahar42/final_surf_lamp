/**
 * Wind Threshold Range Feature
 * Handles wind speed threshold range slider with dual handles
 */

const WindThreshold = {
    updateTimeout: null,

    init: function() {
        const sliderElement = document.getElementById('windSlider');
        const statusDiv = document.getElementById('wind-threshold-status');
        const minInput = document.getElementById('windThresholdMin');
        const maxInput = document.getElementById('windThresholdMax');

        if (!sliderElement || !statusDiv || !minInput) return;

        const currentMin = parseFloat(minInput.value) || DashboardConfig.LIMITS.WIND_THRESHOLD_MIN_KNOTS;
        const currentMax = maxInput?.value ? parseFloat(maxInput.value) : DashboardConfig.LIMITS.WIND_THRESHOLD_MAX_KNOTS;

        noUiSlider.create(sliderElement, {
            start: [currentMin, currentMax],
            connect: true,
            range: {
                min: DashboardConfig.LIMITS.WIND_THRESHOLD_MIN_KNOTS,
                max: DashboardConfig.LIMITS.WIND_THRESHOLD_MAX_KNOTS
            },
            step: 1,
            tooltips: [true, true],
            format: {
                to: value => Math.round(value),
                from: value => parseInt(value)
            }
        });

        const slider = sliderElement.noUiSlider;

        slider.on('update', values => {
            minInput.value = values[0];
            if (maxInput) maxInput.value = values[1];
        });

        slider.on('change', async values => {
            const thresholdMin = parseInt(values[0]);
            const thresholdMax = parseInt(values[1]);

            if (this.updateTimeout) clearTimeout(this.updateTimeout);

            this.updateTimeout = setTimeout(async () => {
                StatusMessage.loading(statusDiv);

                const result = await ApiClient.post(DashboardConfig.API.UPDATE_WIND_THRESHOLD, {
                    threshold_min: thresholdMin,
                    threshold_max: thresholdMax
                });

                if (result.ok) {
                    StatusMessage.success(statusDiv, result.data.message);
                } else {
                    StatusMessage.error(statusDiv, 'Error: ' + result.data.message);
                }
            }, 300);
        });
    }
};

if (typeof window !== 'undefined') {
    window.WindThreshold = WindThreshold;
}
