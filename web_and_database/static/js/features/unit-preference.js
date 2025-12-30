/**
 * Unit Preference Feature
 * Handles toggling between meters and feet for wave height ONLY
 * Wind speed is ALWAYS in knots regardless of preference
 */

const UnitPreference = {
    currentUnit: 'meters', // Default

    /**
     * Initialize unit preference toggle
     * @param {string} initialUnit - Current unit preference ('meters' or 'feet')
     */
    init: function(initialUnit) {
        this.currentUnit = initialUnit || 'meters';

        const toggleBtn = document.getElementById('unitToggle');
        const statusDiv = document.getElementById('unit-status');

        if (!toggleBtn || !statusDiv) {
            console.error('UnitPreference: Required elements not found');
            return;
        }

        // Add click handler
        toggleBtn.addEventListener('click', async () => {
            // Toggle between meters and feet
            const newUnit = this.currentUnit === 'meters' ? 'feet' : 'meters';

            StatusMessage.loading(statusDiv);

            // Make API request
            const result = await ApiClient.post(
                DashboardConfig.API.UPDATE_UNIT_PREFERENCE,
                { unit_preference: newUnit }
            );

            if (result.ok) {
                StatusMessage.success(statusDiv, 'Units updated! Refreshing...');

                // Reload page after short delay to show new units
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                StatusMessage.error(statusDiv, 'Error: ' + result.data.message);
            }
        });
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.UnitPreference = UnitPreference;
}
