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

        const buttons = [
            document.getElementById('unitToggle'),
            document.getElementById('unitToggleMobile')
        ].filter(el => el !== null);

        const statusDivs = [
            document.getElementById('unit-status'),
            document.getElementById('unit-status-mobile')
        ].filter(el => el !== null);

        if (buttons.length === 0) {
            console.error('UnitPreference: No toggle buttons found');
            return;
        }

        // Add click handler to all buttons
        buttons.forEach(btn => {
            btn.addEventListener('click', async () => {
                // Toggle between meters and feet
                const newUnit = this.currentUnit === 'meters' ? 'feet' : 'meters';

                statusDivs.forEach(d => StatusMessage.loading(d));

                // Make API request
                const result = await ApiClient.post(
                    DashboardConfig.API.UPDATE_UNIT_PREFERENCE,
                    { unit_preference: newUnit }
                );

                if (result.ok) {
                    statusDivs.forEach(d => StatusMessage.success(d, 'Units updated! Refreshing...'));

                    // Reload page after short delay to show new units
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    statusDivs.forEach(d => StatusMessage.error(d, 'Error: ' + result.data.message));
                }
            });
        });
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.UnitPreference = UnitPreference;
}
