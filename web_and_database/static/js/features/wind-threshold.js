/**
 * Wind Threshold Feature
 * Handles wind speed threshold update events
 */

const WindThreshold = {
    /**
     * Initialize wind threshold update handler
     */
    init: function() {
        const updateBtn = document.getElementById('updateWindThreshold');
        const thresholdInput = document.getElementById('windThreshold');
        const statusDiv = document.getElementById('wind-threshold-status');

        if (!updateBtn || !thresholdInput || !statusDiv) {
            console.error('WindThreshold: Required elements not found');
            return;
        }

        updateBtn.addEventListener('click', async function() {
            const threshold = parseInt(thresholdInput.value);
            const unit = thresholdInput.dataset.unit;

            // Convert to knots if user prefers mph
            const thresholdKnots = (unit === 'feet')
                ? Math.round(threshold / DashboardConfig.CONVERSIONS.KNOTS_TO_MPH)
                : threshold;

            StatusMessage.loading(statusDiv);

            // Make API request
            const result = await ApiClient.post(
                DashboardConfig.API.UPDATE_WIND_THRESHOLD,
                { threshold: thresholdKnots }
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
