/**
 * Arduino Management Feature
 * Handles adding/linking new Arduino devices from the dashboard
 */

const ArduinoManagement = {
    /**
     * Initialize the feature
     */
    init: function() {
        // Desktop Form Set
        const desktopSet = {
            showAddBtn: document.getElementById('showAddArduinoBtn'),
            form: document.getElementById('addArduinoForm'),
            cancelBtn: document.getElementById('cancelAddArduino'),
            submitBtn: document.getElementById('submitAddArduino'),
            idInput: document.getElementById('newArduinoId'),
            locationInput: document.getElementById('newArduinoLocation')
        };

        // Mobile Form Set
        const mobileSet = {
            showAddBtn: document.getElementById('showAddArduinoBtnMobile'),
            form: document.getElementById('addArduinoFormMobile'),
            cancelBtn: document.getElementById('cancelAddArduinoMobile'),
            submitBtn: document.getElementById('submitAddArduinoMobile'),
            idInput: document.getElementById('newArduinoIdMobile'),
            locationInput: document.getElementById('newArduinoLocationMobile')
        };

        if (desktopSet.showAddBtn && desktopSet.form) {
            this.bindEvents(desktopSet);
        }
        if (mobileSet.showAddBtn && mobileSet.form) {
            this.bindEvents(mobileSet);
        }
    },

    /**
     * Bind event listeners for a form set
     * @param {Object} set - Object containing DOM elements for a form
     */
    bindEvents: function(set) {
        if (!set.showAddBtn) return;

        set.showAddBtn.addEventListener('click', () => {
            set.form.classList.toggle('hidden');
        });

        if (set.cancelBtn) {
            set.cancelBtn.addEventListener('click', () => {
                set.form.classList.add('hidden');
            });
        }

        if (set.submitBtn) {
            set.submitBtn.addEventListener('click', () => this.handleLinkArduino(set));
        }
    },

    /**
     * Handle the link arduino submission
     * @param {Object} set - The form set being submitted
     */
    handleLinkArduino: async function(set) {
        const arduinoId = set.idInput.value;
        const location = set.locationInput.value;

        if (!arduinoId) {
            StatusMessages.show('Please enter an Arduino ID', 'error');
            return;
        }

        // Disable button state
        set.submitBtn.disabled = true;
        const originalText = set.submitBtn.textContent;
        set.submitBtn.textContent = 'Linking...';

        try {
            // Note: APIClient might be ApiClient in this project (check config.js vs others)
            // dashboard uses ApiClient (uppercase C is common in some files, let's stick to project convention)
            const client = window.ApiClient || window.APIClient;
            
            const response = await client.post('/add-arduino', {
                arduino_id: arduinoId,
                location: location
            });

            if (response.ok || response.success) {
                StatusMessages.show('Lamp linked successfully!', 'success');
                // Reload page to show new lamp
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                const msg = response.data ? response.data.message : (response.message || 'Error linking lamp');
                StatusMessages.show(msg, 'error');
                set.submitBtn.disabled = false;
                set.submitBtn.textContent = originalText;
            }
        } catch (error) {
            console.error('Link lamp error:', error);
            StatusMessages.show('Network error. Please try again.', 'error');
            set.submitBtn.disabled = false;
            set.submitBtn.textContent = originalText;
        }
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.ArduinoManagement = ArduinoManagement;
}
