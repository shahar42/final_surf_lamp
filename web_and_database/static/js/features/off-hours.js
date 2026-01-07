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
        // Desktop Elements
        const customInputs = document.getElementById('customTimeInputs');
        const customBtn = document.getElementById('customPresetBtn');
        const updateBtn = document.getElementById('updateOffTimes');
        
        // Mobile Elements
        const customInputsMobile = document.getElementById('customTimeInputsMobile');
        const customBtnMobile = document.getElementById('customPresetBtnMobile');
        const updateBtnMobile = document.getElementById('updateOffTimesMobile');

        // Setup preset button handlers (these share the class .preset-btn so we just need to pass both input containers to hide)
        this.setupPresetButtons([customInputs, customInputsMobile]);

        // Setup custom button handlers
        if (customBtn && customInputs) {
            this.setupCustomButton(customBtn, customInputs);
        }
        if (customBtnMobile && customInputsMobile) {
            this.setupCustomButton(customBtnMobile, customInputsMobile);
        }

        // Setup apply button handlers
        if (updateBtn) {
            this.setupApplyButton(updateBtn, customInputs, 'offTimeStart', 'offTimeEnd');
        }
        if (updateBtnMobile) {
            this.setupApplyButton(updateBtnMobile, customInputsMobile, 'offTimeStartMobile', 'offTimeEndMobile');
        }
    },

    /**
     * Setup preset button click handlers
     * @param {Array} inputContainers - Array of custom input divs to hide when preset is clicked
     */
    setupPresetButtons: function(inputContainers) {
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const startTime = btn.getAttribute('data-start');
                const endTime = btn.getAttribute('data-end');
                const isActive = btn.classList.contains('bg-orange-600/80');

                // Hide all custom input containers
                inputContainers.forEach(container => {
                    if (container) container.classList.add('hidden');
                });

                // Toggle: if active → disable, if inactive → enable
                this.updateOffHours(startTime, endTime, !isActive);
            });
        });
    },

    /**
     * Setup custom button click handler
     */
    setupCustomButton: function(btn, inputs) {
        btn.addEventListener('click', () => {
            const isActive = btn.classList.contains('bg-orange-600/80');

            if (isActive) {
                // Already active → Disable
                this.updateOffHours(null, null, false);
                inputs.classList.add('hidden');
            } else {
                // Inactive → Open drawer for custom times
                inputs.classList.remove('hidden');
            }
        });
    },

    /**
     * Setup apply button in custom drawer
     */
    setupApplyButton: function(btn, inputs, startId, endId) {
        btn.addEventListener('click', () => {
            const startTime = document.getElementById(startId).value;
            const endTime = document.getElementById(endId).value;

            // Apply the custom times
            this.updateOffHours(startTime, endTime, true);

            // Close the drawer
            if (inputs) {
                inputs.classList.add('hidden');
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
        // Update both Desktop and Mobile status indicators
        const elements = [
            { status: document.getElementById('sleepModeStatus'), msg: document.getElementById('off-times-status') },
            { status: document.getElementById('sleepModeStatusMobile'), msg: document.getElementById('off-times-status-mobile') }
        ];

        // Optimistic UI update
        this.resetButtonStyles();

        elements.forEach(({ status }) => {
            if (status) {
                if (!enabled) {
                    status.textContent = 'DISABLED';
                    status.className = 'text-xs font-bold uppercase tracking-wider text-white/50';
                } else {
                    status.textContent = 'ACTIVE';
                    status.className = 'text-xs font-bold uppercase tracking-wider text-orange-500';
                }
            }
        });

        if (enabled) {
             // Highlight matching preset button or custom button
            this.highlightActiveButton(startTime);
        }

        // Show loading in all message areas
        elements.forEach(({ msg }) => {
            if (msg) StatusMessage.loading(msg);
        });

        // Make API request
        const result = await ApiClient.post(
            DashboardConfig.API.UPDATE_OFF_TIMES,
            {
                enabled: enabled,
                start_time: startTime,
                end_time: endTime
            }
        );

        // Show result in all message areas
        elements.forEach(({ msg }) => {
            if (msg) {
                if (result.ok) {
                    StatusMessage.warning(msg, '✓ ' + result.data.message, true);
                } else {
                    StatusMessage.error(msg, 'Error: ' + result.data.message);
                }
            }
        });
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

        // Reset custom buttons (both desktop and mobile)
        ['customPresetBtn', 'customPresetBtnMobile'].forEach(id => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.classList.remove(...this.ACTIVE_CLASSES);
                btn.classList.add(...this.INACTIVE_CLASSES);
            }
        });
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

        // If no preset matched, highlight custom buttons
        if (!matched) {
            ['customPresetBtn', 'customPresetBtnMobile'].forEach(id => {
                const btn = document.getElementById(id);
                if (btn) {
                    btn.classList.remove(...this.INACTIVE_CLASSES);
                    btn.classList.add(...this.ACTIVE_CLASSES);
                }
            });
        }
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.OffHours = OffHours;
}
