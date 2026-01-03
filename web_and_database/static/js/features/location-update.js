/**
 * Location Update Feature
 * Handles location dropdown change events
 */

const LocationUpdate = {
    /**
     * Initialize location update handler
     * @param {string} currentLocation - User's current location
     */
    init: function(currentLocation) {
        const locationSelect = document.getElementById('locationSelect');
        const statusDiv = document.getElementById('location-status');

        if (!locationSelect || !statusDiv) {
            console.error('LocationUpdate: Required elements not found');
            return;
        }

        locationSelect.addEventListener('change', async function() {
            const newLocation = this.value;

            // No change
            if (newLocation === currentLocation) return;

            // Disable dropdown during update
            locationSelect.disabled = true;
            StatusMessage.loading(statusDiv);

            // Make API request
            const result = await ApiClient.post(
                DashboardConfig.API.UPDATE_LOCATION,
                { location: newLocation }
            );

            // Re-enable dropdown
            locationSelect.disabled = false;

            if (result.ok) {
                StatusMessage.success(statusDiv, result.data.message);

                // Update selected option
                const oldOption = document.querySelector(`#locationSelect option[value='${currentLocation}']`);
                const newOption = document.querySelector(`#locationSelect option[value='${newLocation}']`);

                if (oldOption) oldOption.removeAttribute('selected');
                if (newOption) newOption.setAttribute('selected', 'selected');

                // Update current location for future comparisons
                currentLocation = newLocation;
            } else {
                StatusMessage.error(statusDiv, 'Error: ' + result.data.message);
                // Reset dropdown to original value
                locationSelect.value = currentLocation;
            }
        });
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.LocationUpdate = LocationUpdate;
}
