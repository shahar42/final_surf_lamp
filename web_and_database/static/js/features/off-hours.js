/**
 * Off Hours Feature (Sleep Mode)
 * Handles preset buttons, custom time inputs, and toggle logic
 */

const OffHours = {
    // CSS classes for active/inactive button states
    INACTIVE_CLASSES: ['bg-white/10', 'hover:bg-white/20', 'text-white/80', 'border-white/20'],
    ACTIVE_CLASSES: ['bg-orange-600/80', 'border-orange-500', 'text-white', 'font-semibold', 'shadow-[0_0_15px_rgba(234,88,12,0.3)]'],

    /**
     * Initialize off hours feature
     */
    init: function() {
        const statusDiv = document.getElementById('off-times-status');
        const modeStatus = document.getElementById('sleepModeStatus');
        const customInputs = document.getElementById('customTimeInputs');
        const customBtn = document.getElementById('customPresetBtn');
        const updateBtn = document.getElementById('updateOffTimes');

        if (!statusDiv || !modeStatus) {
            console.error('OffHours: Required elements not found');
            return;
        }

        // Setup preset button handlers
        this.setupPresetButtons(customInputs);

        // Setup custom button handler
        if (customBtn && customInputs) {
            this.setupCustomButton(customBtn, customInputs);
        }

        // Setup apply button handler
        if (updateBtn) {
            this.setupApplyButton(updateBtn);
        }
    },

    /**
     * Setup preset button click handlers
     */
    setupPresetButtons: function(customInputs) {
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const startTime = btn.getAttribute('data-start');
                const endTime = btn.getAttribute('data-end');
                const isActive = btn.classList.contains('bg-orange-600/80');

                // Hide custom inputs if open
                if (customInputs) {
                    customInputs.classList.add('hidden');
                }

                // Toggle: if active → disable, if inactive → enable
                this.updateOffHours(startTime, endTime, !isActive);
            });
        });
    },

    /**
     * Setup custom button click handler
     */
    setupCustomButton: function(customBtn, customInputs) {
        customBtn.addEventListener('click', () => {
            const isActive = customBtn.classList.contains('bg-orange-600/80');

            if (isActive) {
                // Already active → Disable
                this.updateOffHours(null, null, false);
                customInputs.classList.add('hidden');
            } else {
                // Inactive → Open drawer for custom times
                customInputs.classList.remove('hidden');
            }
        });
    },

    /**
     * Setup apply button in custom drawer
     */
    setupApplyButton: function(updateBtn) {
        updateBtn.addEventListener('click', () => {
            const startTime = document.getElementById('offTimeStart').value;
            const endTime = document.getElementById('offTimeEnd').value;
            const customInputs = document.getElementById('customTimeInputs');

            // Apply the custom times
            this.updateOffHours(startTime, endTime, true);

            // Close the drawer
            if (customInputs) {
                customInputs.classList.add('hidden');
            }
        });
    },

    /**
     * Update off hours setting
     * @param {string} startTime - Start time (HH:MM format)
     * @param {string} endTime - End time (HH:MM format)
     * @param {boolean} enabled - Enable or disable off hours
     */
    updateOffHours: async function(startTime, endTime, enabled) {
        const statusDiv = document.getElementById('off-times-status');
        const modeStatus = document.getElementById('sleepModeStatus');

        // Optimistic UI update
        this.resetButtonStyles();

        if (!enabled) {
            modeStatus.textContent = 'DISABLED';
            modeStatus.className = 'text-xs font-bold uppercase tracking-wider text-white/50';
        } else {
            modeStatus.textContent = 'ACTIVE';
            modeStatus.className = 'text-xs font-bold uppercase tracking-wider text-orange-500';

            // Highlight matching preset button or custom button
            this.highlightActiveButton(startTime);
        }

        StatusMessage.loading(statusDiv);

        // Make API request
        const result = await ApiClient.post(
            DashboardConfig.API.UPDATE_OFF_TIMES,
            {
                enabled: enabled,
                start_time: startTime,
                end_time: endTime
            }
        );

        if (result.ok) {
            StatusMessage.warning(statusDiv, '✓ ' + result.data.message, true);
        } else {
            StatusMessage.error(statusDiv, 'Error: ' + result.data.message);
        }
    },

    /**
     * Reset all button styles to inactive state
     */
    resetButtonStyles: function() {
        // Reset preset buttons
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.classList.remove(...this.ACTIVE_CLASSES);
            btn.classList.add(...this.INACTIVE_CLASSES);
        });

        // Reset custom button
        const customBtn = document.getElementById('customPresetBtn');
        if (customBtn) {
            customBtn.classList.remove(...this.ACTIVE_CLASSES);
            customBtn.classList.add(...this.INACTIVE_CLASSES);
        }
    },

    /**
     * Highlight the active button based on start time
     * @param {string} startTime - Start time to match against presets
     */
    highlightActiveButton: function(startTime) {
        let matched = false;

        // Try to match a preset button
        document.querySelectorAll('.preset-btn').forEach(btn => {
            if (btn.getAttribute('data-start') === startTime) {
                btn.classList.remove(...this.INACTIVE_CLASSES);
                btn.classList.add(...this.ACTIVE_CLASSES);
                matched = true;
            }
        });

        // If no preset matched, highlight custom button
        if (!matched) {
            const customBtn = document.getElementById('customPresetBtn');
            if (customBtn) {
                customBtn.classList.remove(...this.INACTIVE_CLASSES);
                customBtn.classList.add(...this.ACTIVE_CLASSES);
            }
        }
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.OffHours = OffHours;
}
