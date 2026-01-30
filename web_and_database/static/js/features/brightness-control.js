/**
 * Brightness Control Feature
 * Handles brightness button clicks and active state management
 */

const BrightnessControl = {
    // CSS classes matching the sleep mode pattern (blue theme)
    INACTIVE_CLASSES: ['bg-white/5', 'hover:bg-white/10', 'text-white/40', 'border-white/5'],
    ACTIVE_CLASSES: ['bg-blue-600/20', 'border-blue-500/50', 'text-blue-400', 'font-bold', 'shadow-lg', 'shadow-blue-900/20'],

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

        // Set initial active state based on current brightness
        this.setActiveButton(buttons, currentBrightness);

        // Add click handler to each button
        buttons.forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.stopPropagation(); // Prevent event bubbling
                const selectedBrightness = parseFloat(this.getAttribute('data-brightness'));

                statusDivs.forEach(d => StatusMessage.loading(d));

                // Make API request
                const result = await ApiClient.post(
                    DashboardConfig.API.UPDATE_BRIGHTNESS,
                    { brightness: selectedBrightness }
                );

                if (result.ok) {
                    // Update active state across all buttons (syncs desktop/mobile buttons)
                    BrightnessControl.setActiveButton(buttons, selectedBrightness);
                    statusDivs.forEach(d => StatusMessage.success(d, result.data.message));
                } else {
                    statusDivs.forEach(d => StatusMessage.error(d, 'Error: ' + result.data.message));
                }
            });
        });
    },

    /**
     * Set the active button based on brightness value
     * @param {NodeList} buttons - All brightness buttons
     * @param {number} brightness - Current brightness level
     */
    setActiveButton: function(buttons, brightness) {
        buttons.forEach(btn => {
            const btnBrightness = parseFloat(btn.getAttribute('data-brightness'));

            if (Math.abs(btnBrightness - brightness) < 0.01) {
                // Active button - apply blue theme
                btn.classList.remove(...this.INACTIVE_CLASSES);
                btn.classList.add(...this.ACTIVE_CLASSES);
            } else {
                // Inactive button
                btn.classList.remove(...this.ACTIVE_CLASSES);
                btn.classList.add(...this.INACTIVE_CLASSES);
            }
        });
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.BrightnessControl = BrightnessControl;
}
