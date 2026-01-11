/**
 * Wind Threshold Range Feature
 * Handles wind speed threshold range slider with dual handles
 */

const WindThreshold = {
    updateTimeout: null,

    /**
     * Initialize wind threshold range sliders
     */
    init: function() {
        // Desktop elements
        const sliderElement = document.getElementById('windSlider');
        const statusDiv = document.getElementById('wind-threshold-status');
        const minInput = document.getElementById('windThresholdMin');
        const maxInput = document.getElementById('windThresholdMax');

        // Mobile elements
        const sliderElementMobile = document.getElementById('windSliderMobile');
        const statusDivMobile = document.getElementById('wind-threshold-status-mobile');
        const minInputMobile = document.getElementById('windThresholdMinMobile');
        const maxInputMobile = document.getElementById('windThresholdMaxMobile');

        // Setup desktop slider
        if (sliderElement && statusDiv && minInput) {
            this.setupSlider(sliderElement, statusDiv, minInput, maxInput, [statusDivMobile], [minInputMobile, maxInputMobile]);
        }

        // Setup mobile slider
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
        // Get current values
        const currentMin = parseFloat(minIn.value) || DashboardConfig.LIMITS.WIND_THRESHOLD_MIN_KNOTS;
        const currentMax = maxIn.value ? parseFloat(maxIn.value) : DashboardConfig.LIMITS.WIND_THRESHOLD_MAX_KNOTS;

        // Slider range bounds (knots)
        const sliderMin = DashboardConfig.LIMITS.WIND_THRESHOLD_MIN_KNOTS;
        const sliderMax = DashboardConfig.LIMITS.WIND_THRESHOLD_MAX_KNOTS;

        // Create dual-handle range slider
        noUiSlider.create(element, {
            start: [currentMin, currentMax],
            connect: true,
            range: {
                'min': sliderMin,
                'max': sliderMax
            },
            step: 1,
            tooltips: [true, true],
            format: {
                to: function(value) { return Math.round(value); },
                from: function(value) { return parseInt(value); }
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
            const thresholdMin = parseInt(values[0]);
            const thresholdMax = parseInt(values[1]);

            if (this.updateTimeout) {
                clearTimeout(this.updateTimeout);
            }

            this.updateTimeout = setTimeout(async () => {
                const statusDivs = [status, ...peerStatuses].filter(d => d !== null);
                
                statusDivs.forEach(d => StatusMessage.loading(d));

                const result = await ApiClient.post(
                    DashboardConfig.API.UPDATE_WIND_THRESHOLD,
                    {
                        threshold_min: thresholdMin,
                        threshold_max: thresholdMax
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
    window.WindThreshold = WindThreshold;
}
