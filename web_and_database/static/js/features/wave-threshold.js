/**
 * Wave Threshold Feature
 * Handles wave height threshold update events
 */

const WaveThreshold = {
    /**
     * Initialize wave threshold update handler
     */
    init: function() {
        const updateBtn = document.getElementById('updateThreshold');
        const thresholdInput = document.getElementById('waveThreshold');
        const statusDiv = document.getElementById('threshold-status');

        if (!updateBtn || !thresholdInput || !statusDiv) {
            console.error('WaveThreshold: Required elements not found');
            return;
        }

        updateBtn.addEventListener('click', async function() {
            const threshold = parseFloat(thresholdInput.value);
            const unit = thresholdInput.dataset.unit;

            // Convert to meters if user prefers feet
            const thresholdMeters = (unit === 'feet')
                ? threshold / DashboardConfig.CONVERSIONS.METERS_TO_FEET
                : threshold;

            StatusMessage.loading(statusDiv);

            // Make API request
            const result = await ApiClient.post(
                DashboardConfig.API.UPDATE_THRESHOLD,
                { threshold: thresholdMeters }
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
    window.WaveThreshold = WaveThreshold;
}
