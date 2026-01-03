/**
 * Brightness Control Feature
 * Handles brightness button clicks and active state management
 */

const BrightnessControl = {
    /**
     * Initialize brightness control
     * @param {number} currentBrightness - Current brightness level (0.0-1.0)
     */
    init: function(currentBrightness) {
        const buttons = document.querySelectorAll('.brightness-btn');
        const statusDiv = document.getElementById('brightness-status');

        if (!buttons.length || !statusDiv) {
            console.error('BrightnessControl: Required elements not found');
            return;
        }

        // Clear all active states first (defensive programming)
        buttons.forEach(btn => btn.classList.remove('brightness-active'));

        // Set initial active state based on current brightness
        buttons.forEach(btn => {
            const brightness = parseFloat(btn.getAttribute('data-brightness'));

            // Set active state if matches current brightness (with tolerance)
            if (Math.abs(brightness - currentBrightness) < 0.01) {
                btn.classList.add('brightness-active');
            }

            // Add click handler
            btn.addEventListener('click', async function() {
                const selectedBrightness = parseFloat(this.getAttribute('data-brightness'));

                StatusMessage.loading(statusDiv);

                // Make API request
                const result = await ApiClient.post(
                    DashboardConfig.API.UPDATE_BRIGHTNESS,
                    { brightness: selectedBrightness }
                );

                if (result.ok) {
                    // Update active state
                    buttons.forEach(b => b.classList.remove('brightness-active'));
                    this.classList.add('brightness-active');

                    StatusMessage.success(statusDiv, result.data.message);
                } else {
                    StatusMessage.error(statusDiv, 'Error: ' + result.data.message);
                }
            });
        });
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.BrightnessControl = BrightnessControl;
}
