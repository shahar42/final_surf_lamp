/**
 * Wave Threshold Range Feature
 * Handles wave height threshold range slider with dual handles
 */

const WaveThreshold = {
    updateTimeout: null,

    init: function() {
        const sliderElement = document.getElementById('waveSlider');
        const statusDiv = document.getElementById('threshold-status');
        const minInput = document.getElementById('waveThresholdMin');
        const maxInput = document.getElementById('waveThresholdMax');

        if (!sliderElement || !statusDiv || !minInput) return;

        const unit = minInput.dataset.unit;
        const isFeet = unit === 'feet';

        const currentMin = parseFloat(minInput.value) || (isFeet ? DashboardConfig.LIMITS.WAVE_THRESHOLD_MIN_FEET : DashboardConfig.LIMITS.WAVE_THRESHOLD_MIN_METERS);
        const currentMax = maxInput?.value ? parseFloat(maxInput.value) : (isFeet ? DashboardConfig.LIMITS.WAVE_THRESHOLD_MAX_FEET : DashboardConfig.LIMITS.WAVE_THRESHOLD_MAX_METERS);

        const sliderMin = isFeet ? DashboardConfig.LIMITS.WAVE_THRESHOLD_MIN_FEET : DashboardConfig.LIMITS.WAVE_THRESHOLD_MIN_METERS;
        const sliderMax = isFeet ? DashboardConfig.LIMITS.WAVE_THRESHOLD_MAX_FEET : DashboardConfig.LIMITS.WAVE_THRESHOLD_MAX_METERS;

        noUiSlider.create(sliderElement, {
            start: [currentMin, currentMax],
            connect: true,
            range: { min: sliderMin, max: sliderMax },
            step: isFeet ? 0.3 : 0.1,
            tooltips: [true, true],
            format: {
                to: value => parseFloat(value.toFixed(1)),
                from: value => parseFloat(value)
            }
        });

        const slider = sliderElement.noUiSlider;

        slider.on('update', values => {
            minInput.value = values[0];
            if (maxInput) maxInput.value = values[1];
        });

        slider.on('change', async values => {
            const thresholdMin = parseFloat(values[0]);
            const thresholdMax = parseFloat(values[1]);
            const thresholdMinMeters = isFeet ? thresholdMin / DashboardConfig.CONVERSIONS.METERS_TO_FEET : thresholdMin;
            const thresholdMaxMeters = isFeet ? thresholdMax / DashboardConfig.CONVERSIONS.METERS_TO_FEET : thresholdMax;

            if (this.updateTimeout) clearTimeout(this.updateTimeout);

            this.updateTimeout = setTimeout(async () => {
                StatusMessage.loading(statusDiv);

                const result = await ApiClient.post(DashboardConfig.API.UPDATE_THRESHOLD, {
                    threshold_min: thresholdMinMeters,
                    threshold_max: thresholdMaxMeters
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
    window.WaveThreshold = WaveThreshold;
}
