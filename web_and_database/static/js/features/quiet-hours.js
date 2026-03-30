/**
 * Quiet Hours Toggle Feature
 * Handles quiet hours toggle button clicks (10pm-6am top LED mode)
 */

const QuietHours = {
    /**
     * Initialize quiet hours toggle
     * @param {boolean} currentlyEnabled - Whether quiet hours is currently enabled
     */
    init: function(currentlyEnabled) {
        const buttons = [
            document.getElementById('quietHoursToggle'),
            document.getElementById('quietHoursToggleMobile')
        ].filter(el => el !== null);

        if (!buttons.length) {
            console.error('QuietHours: No toggle buttons found');
            return;
        }

        // Add click handler to all buttons
        buttons.forEach(btn => {
            btn.addEventListener('click', async function() {
                // Get current state from button text
                const isCurrentlyEnabled = this.textContent.trim() === 'Turned On';
                const newState = !isCurrentlyEnabled;

                // Make API request
                const result = await ApiClient.post(
                    DashboardConfig.API.TOGGLE_QUIET_HOURS,
                    { enabled: newState }
                );

                if (result.ok) {
                    // Update all buttons (syncs desktop/mobile)
                    buttons.forEach(b => {
                        if (newState) {
                            // Enable state - solid blue background (matches LED Configure button)
                            b.classList.remove('text-white/50', 'border', 'border-white/20');
                            b.classList.add('bg-blue-500', 'text-white');
                            b.textContent = 'Turned On';
                        } else {
                            // Disable state - grayed out
                            b.classList.remove('bg-blue-500', 'text-white');
                            b.classList.add('text-white/50', 'border', 'border-white/20');
                            b.textContent = 'Turned Off';
                        }
                    });
                } else {
                    // If API fails, revert UI to show actual state
                    buttons.forEach(b => {
                        if (isCurrentlyEnabled) {
                            b.classList.remove('text-white/50', 'border', 'border-white/20');
                            b.classList.add('bg-blue-500', 'text-white');
                            b.textContent = 'Turned On';
                        } else {
                            b.classList.remove('bg-blue-500', 'text-white');
                            b.classList.add('text-white/50', 'border', 'border-white/20');
                            b.textContent = 'Turned Off';
                        }
                    });
                }
            });
        });
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.QuietHours = QuietHours;
}
