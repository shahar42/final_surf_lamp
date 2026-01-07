/**
 * Wave Threshold Range Feature
 * Handles wave height threshold range slider with dual handles
 */

const WaveThreshold = {
    updateTimeout: null,

    /**
     * Initialize wave threshold range sliders
     */
    init: function() {
        // Desktop elements
        const sliderElement = document.getElementById('waveSlider');
        const statusDiv = document.getElementById('threshold-status');
        const minInput = document.getElementById('waveThresholdMin');
        const maxInput = document.getElementById('waveThresholdMax');

        // Mobile elements
        const sliderElementMobile = document.getElementById('waveSliderMobile');
        const statusDivMobile = document.getElementById('threshold-status-mobile');
        const minInputMobile = document.getElementById('waveThresholdMinMobile');
        const maxInputMobile = document.getElementById('waveThresholdMaxMobile');

        // Setup desktop slider if exists
        if (sliderElement && statusDiv && minInput) {
            this.setupSlider(sliderElement, statusDiv, minInput, maxInput, [statusDivMobile], [minInputMobile, maxInputMobile]);
        }

        // Setup mobile slider if exists
        if (sliderElementMobile && statusDivMobile && minInputMobile) {
            this.setupSlider(sliderElementMobile, statusDivMobile, minInputMobile, maxInputMobile, [statusDiv], [minInput, maxInput]);
        }
    },

    /**
     * Shared slider setup logic
     * @param {HTMLElement} element - The main slider container
     * @param {HTMLElement} status - Primary status message div
     * @param {HTMLElement} minIn - Primary min value input
     * @param {HTMLElement} maxIn - Primary max value input
     * @param {Array} peerStatuses - Array of status divs in other views to sync
     * @param {Array} peerInputs - Array of hidden inputs [min, max] in other views to sync
     */
    setupSlider: function(element, status, minIn, maxIn, peerStatuses, peerInputs) {
        const unit = minIn.dataset.unit;
        const isFeet = unit === 'feet';

        // Get current values
        const currentMin = parseFloat(minIn.value) || (isFeet ? DashboardConfig.LIMITS.WAVE_THRESHOLD_MIN_FEET : DashboardConfig.LIMITS.WAVE_THRESHOLD_MIN_METERS);
        const currentMax = maxIn.value ? parseFloat(maxIn.value) : (isFeet ? DashboardConfig.LIMITS.WAVE_THRESHOLD_MAX_FEET : DashboardConfig.LIMITS.WAVE_THRESHOLD_MAX_METERS);

        // Slider range bounds
        const sliderMin = isFeet ? DashboardConfig.LIMITS.WAVE_THRESHOLD_MIN_FEET : DashboardConfig.LIMITS.WAVE_THRESHOLD_MIN_METERS;
        const sliderMax = isFeet ? DashboardConfig.LIMITS.WAVE_THRESHOLD_MAX_FEET : DashboardConfig.LIMITS.WAVE_THRESHOLD_MAX_METERS;

        // Create dual-handle range slider
        noUiSlider.create(element, {
            start: [currentMin, currentMax],
            connect: true,
            range: {
                'min': sliderMin,
                'max': sliderMax
            },
            step: isFeet ? 0.3 : 0.1,
            tooltips: [true, true],
            format: {
                to: function(value) { return parseFloat(value.toFixed(1)); },
                from: function(value) { return parseFloat(value); }
            }
        });

        const slider = element.noUiSlider;

        // Store values in hidden inputs when slider updates
        slider.on('update', (values) => {
            // Update primary inputs
            minIn.value = values[0];
            if (maxIn) maxIn.value = values[1];
            
            // Sync peer inputs
            if (peerInputs && peerInputs.length >= 2) {
                if (peerInputs[0]) peerInputs[0].value = values[0];
                if (peerInputs[1]) peerInputs[1].value = values[1];
            }
        });

        // Auto-update on slider change (release)
        slider.on('change', async (values) => {
            const thresholdMin = parseFloat(values[0]);
            const thresholdMax = parseFloat(values[1]);

            // Convert to meters if needed
            const thresholdMinMeters = isFeet ? thresholdMin / DashboardConfig.CONVERSIONS.METERS_TO_FEET : thresholdMin;
            const thresholdMaxMeters = isFeet ? thresholdMax / DashboardConfig.CONVERSIONS.METERS_TO_FEET : thresholdMax;

            if (this.updateTimeout) {
                clearTimeout(this.updateTimeout);
            }

            this.updateTimeout = setTimeout(async () => {
                const statusDivs = [status, ...peerStatuses].filter(d => d !== null);
                
                statusDivs.forEach(d => StatusMessage.loading(d));

                const result = await ApiClient.post(
                    DashboardConfig.API.UPDATE_THRESHOLD,
                    {
                        threshold_min: thresholdMinMeters,
                        threshold_max: thresholdMaxMeters
                    }
                );

                statusDivs.forEach(d => {
                    if (result.ok) {
                        StatusMessage.success(d, result.data.message);
                    } else {
                        StatusMessage.error(d, 'Error: ' + result.data.message);
                    }
                });
            }, 300);
        });
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.WaveThreshold = WaveThreshold;
}
