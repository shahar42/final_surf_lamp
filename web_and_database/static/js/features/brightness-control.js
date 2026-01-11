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
        const statusDivs = [
            document.getElementById('brightness-status'),
            document.getElementById('brightness-status-mobile')
        ].filter(el => el !== null);

        if (!buttons.length) {
            console.error('BrightnessControl: No buttons found');
            return;
        }

        // Clear all active states first
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

                statusDivs.forEach(d => StatusMessage.loading(d));

                // Make API request
                const result = await ApiClient.post(
                    DashboardConfig.API.UPDATE_BRIGHTNESS,
                    { brightness: selectedBrightness }
                );

                if (result.ok) {
                    // Update active state across all buttons (syncs desktop/mobile buttons)
                    buttons.forEach(b => {
                        const bVal = parseFloat(b.getAttribute('data-brightness'));
                        if (Math.abs(bVal - selectedBrightness) < 0.01) {
                            b.classList.add('brightness-active');
                        } else {
                            b.classList.remove('brightness-active');
                        }
                    });

                    statusDivs.forEach(d => StatusMessage.success(d, result.data.message));
                } else {
                    statusDivs.forEach(d => StatusMessage.error(d, 'Error: ' + result.data.message));
                }
            });
        });
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.BrightnessControl = BrightnessControl;
}
