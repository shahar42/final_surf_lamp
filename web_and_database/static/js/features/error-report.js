/**
 * Error Report Modal
 * Handles error reporting functionality
 */

const ErrorReport = {
    // DOM elements
    modal: null,
    reportBtn: null,
    cancelBtn: null,
    form: null,
    textarea: null,
    charCount: null,
    statusDiv: null,
    submitBtn: null,

    /**
     * Initialize error report modal
     */
    init: function() {
        // Get DOM elements
        this.modal = document.getElementById('errorReportModal');
        this.reportBtn = document.getElementById('reportErrorBtn');
        this.cancelBtn = document.getElementById('cancelErrorReport');
        this.form = document.getElementById('errorReportForm');
        this.textarea = document.getElementById('errorDescription');
        this.charCount = document.getElementById('charCount');
        this.statusDiv = document.getElementById('errorReportStatus');
        this.submitBtn = document.getElementById('submitErrorReport');

        if (!this.modal || !this.reportBtn) {
            console.warn('Error report modal elements not found');
            return;
        }

        // Setup event listeners
        this.setupEventListeners();
    },

    /**
     * Setup all event listeners
     */
    setupEventListeners: function() {
        // Open modal button
        this.reportBtn.addEventListener('click', () => this.openModal());

        // Cancel button
        this.cancelBtn.addEventListener('click', () => this.closeModal());

        // Close on backdrop click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });

        // Character counter
        this.textarea.addEventListener('input', () => {
            this.charCount.textContent = this.textarea.value.length;
        });

        // Form submission
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
    },

    /**
     * Open the error report modal
     */
    openModal: function() {
        ModalManager.open('errorReportModal', this.textarea);
    },

    /**
     * Close the error report modal and reset form
     */
    closeModal: function() {
        ModalManager.close('errorReportModal');
        this.resetForm();
    },

    /**
     * Reset form to initial state
     */
    resetForm: function() {
        this.textarea.value = '';
        this.charCount.textContent = '0';
        this.statusDiv.classList.add('hidden');
        this.submitBtn.disabled = false;
        this.submitBtn.textContent = 'Submit Report';
    },

    /**
     * Handle form submission
     * @param {Event} e - Submit event
     */
    handleSubmit: async function(e) {
        e.preventDefault();

        const description = this.textarea.value.trim();

        // Validate input
        if (!description) {
            this.showStatus('Please enter a description of the error.', 'error');
            return;
        }

        // Disable submit button
        this.submitBtn.disabled = true;
        this.submitBtn.textContent = 'Submitting...';
        this.showStatus('Submitting your report...', 'loading');

        // Submit via ApiClient
        const result = await ApiClient.post(DashboardConfig.API.REPORT_ERROR, {
            error_description: description
        });

        if (result.ok) {
            this.showStatus(result.data.message, 'success');
            // Close modal after 2 seconds
            setTimeout(() => this.closeModal(), DashboardConfig.TIMING.MODAL_AUTO_CLOSE);
        } else {
            this.showStatus('Error: ' + (result.data.message || 'Failed to submit report'), 'error');
            // Re-enable submit button
            this.submitBtn.disabled = false;
            this.submitBtn.textContent = 'Submit Report';
        }
    },

    /**
     * Show status message in modal
     * @param {string} message - Status message
     * @param {string} type - Message type (loading, success, error)
     */
    showStatus: function(message, type) {
        this.statusDiv.textContent = message;
        this.statusDiv.classList.remove('hidden');

        // Apply appropriate styling
        const colorClass = {
            loading: 'text-blue-600',
            success: 'text-green-600',
            error: 'text-red-600'
        }[type] || 'text-gray-600';

        this.statusDiv.className = `mb-4 text-sm ${colorClass}`;
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.ErrorReport = ErrorReport;
}
