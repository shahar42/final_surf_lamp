/**
 * Status Message Utility
 * Centralized handler for status message display
 */

const StatusMessage = {
    /**
     * Display a status message in a given element
     * @param {HTMLElement} element - The element to show the message in
     * @param {string} message - The message text
     * @param {string} type - Message type: 'loading', 'success', 'error'
     * @param {number} autoClearMs - Auto-clear after N milliseconds (0 = no auto-clear)
     */
    show: function(element, message, type = 'loading', autoClearMs = 0) {
        if (!element) {
            console.error('StatusMessage.show: element is null');
            return;
        }

        element.textContent = message;

        // Set color based on type
        switch(type) {
            case 'loading':
                element.style.color = '#ffffff';
                break;
            case 'success':
                element.style.color = '#10b981'; // Green
                break;
            case 'error':
                element.style.color = '#ef4444'; // Red
                break;
            case 'warning':
                element.style.color = '#fb923c'; // Orange
                break;
            default:
                element.style.color = '#ffffff';
        }

        // Auto-clear if specified
        if (autoClearMs > 0) {
            setTimeout(() => {
                this.clear(element);
            }, autoClearMs);
        }
    },

    /**
     * Clear a status message
     * @param {HTMLElement} element - The element to clear
     */
    clear: function(element) {
        if (element) {
            element.textContent = '';
        }
    },

    /**
     * Convenience methods for common use cases
     */
    loading: function(element, message = 'Updating...') {
        this.show(element, message, 'loading');
    },

    success: function(element, message, autoClear = true) {
        const clearTime = autoClear ? DashboardConfig.TIMING.STATUS_MESSAGE_DISPLAY : 0;
        this.show(element, message, 'success', clearTime);
    },

    error: function(element, message) {
        this.show(element, message, 'error');
    },

    warning: function(element, message, autoClear = true) {
        const clearTime = autoClear ? DashboardConfig.TIMING.STATUS_MESSAGE_DISPLAY : 0;
        this.show(element, message, 'warning', clearTime);
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.StatusMessage = StatusMessage;
}
