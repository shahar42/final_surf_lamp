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
        const selects = [
            document.getElementById('locationSelect'),
            document.getElementById('locationSelectMobile')
        ].filter(el => el !== null);

        const statusDivs = [
            document.getElementById('location-status'),
            document.getElementById('location-status-mobile')
        ].filter(el => el !== null);

        if (selects.length === 0) {
            console.error('LocationUpdate: No select elements found');
            return;
        }

        const self = this;
        selects.forEach(select => {
            select.addEventListener('change', async function() {
                const newLocation = this.value;

                // No change
                if (newLocation === currentLocation) return;

                // Disable all dropdowns during update
                selects.forEach(s => s.disabled = true);
                statusDivs.forEach(d => StatusMessage.loading(d));

                // Make API request
                const result = await ApiClient.post(
                    DashboardConfig.API.UPDATE_LOCATION,
                    { location: newLocation }
                );

                // Re-enable all dropdowns
                selects.forEach(s => s.disabled = false);

                if (result.ok) {
                    statusDivs.forEach(d => StatusMessage.success(d, result.data.message));

                    // Update values and selected attributes across all selects
                    selects.forEach(s => {
                        s.value = newLocation;
                        // Update selected option attribute
                        const oldOption = s.querySelector(`option[value='${currentLocation}']`);
                        const newOption = s.querySelector(`option[value='${newLocation}']`);
                        if (oldOption) oldOption.removeAttribute('selected');
                        if (newOption) newOption.setAttribute('selected', 'selected');
                    });

                    // Update current location for future comparisons
                    currentLocation = newLocation;
                } else {
                    statusDivs.forEach(d => StatusMessage.error(d, 'Error: ' + result.data.message));
                    // Reset all dropdowns to original value
                    selects.forEach(s => s.value = currentLocation);
                }
            });
        });
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.LocationUpdate = LocationUpdate;
}
