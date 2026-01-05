/**
 * Arduino Management Feature
 * Handles adding/linking new Arduino devices from the dashboard
 */

const ArduinoManagement = {
    // DOM Elements
    elements: {
        showAddBtn: null,
        form: null,
        cancelBtn: null,
        submitBtn: null,
        idInput: null,
        locationInput: null
    },

    /**
     * Initialize the feature
     */
    init: function() {
        // Get DOM elements
        this.elements.showAddBtn = document.getElementById('showAddArduinoBtn');
        this.elements.form = document.getElementById('addArduinoForm');
        this.elements.cancelBtn = document.getElementById('cancelAddArduino');
        this.elements.submitBtn = document.getElementById('submitAddArduino');
        this.elements.idInput = document.getElementById('newArduinoId');
        this.elements.locationInput = document.getElementById('newArduinoLocation');

        // Only initialize if elements exist
        if (this.elements.showAddBtn && this.elements.form) {
            this.bindEvents();
        }
    },

    /**
     * Bind event listeners
     */
    bindEvents: function() {
        this.elements.showAddBtn.addEventListener('click', () => {
            this.elements.form.classList.toggle('hidden');
        });

        this.elements.cancelBtn.addEventListener('click', () => {
            this.elements.form.classList.add('hidden');
        });

        this.elements.submitBtn.addEventListener('click', () => this.handleLinkArduino());
    },

    /**
     * Handle the link arduino submission
     */
    handleLinkArduino: async function() {
        const arduinoId = this.elements.idInput.value;
        const location = this.elements.locationInput.value;

        if (!arduinoId) {
            StatusMessages.show('Please enter an Arduino ID', 'error');
            return;
        }

        // Disable button state
        this.elements.submitBtn.disabled = true;
        this.elements.submitBtn.textContent = 'Linking...';

        try {
            const response = await APIClient.post('/add-arduino', {
                arduino_id: arduinoId,
                location: location
            });

            if (response.success) {
                StatusMessages.show('Lamp linked successfully!', 'success');
                // Reload page to show new lamp
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                StatusMessages.show(response.message || 'Error linking lamp', 'error');
                this.elements.submitBtn.disabled = false;
                this.elements.submitBtn.textContent = 'Link Lamp';
            }
        } catch (error) {
            console.error('Link lamp error:', error);
            StatusMessages.show('Network error. Please try again.', 'error');
            this.elements.submitBtn.disabled = false;
            this.elements.submitBtn.textContent = 'Link Lamp';
        }
    }
};
