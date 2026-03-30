/**
 * Modal Manager
 * Centralized handler for modal open/close operations
 */

const ModalManager = {
    /**
     * Open a modal
     * @param {string|HTMLElement} modalId - Modal element or ID
     * @param {HTMLElement} focusElement - Optional element to focus after opening
     */
    open: function(modalId, focusElement = null) {
        const modal = typeof modalId === 'string'
            ? document.getElementById(modalId)
            : modalId;

        if (!modal) {
            console.error('ModalManager.open: Modal not found', modalId);
            return;
        }

        modal.classList.remove('hidden');
        modal.classList.add('flex');

        // Focus specified element or first input
        if (focusElement) {
            setTimeout(() => focusElement.focus(), 100);
        } else {
            const firstInput = modal.querySelector('input, textarea');
            if (firstInput) {
                setTimeout(() => firstInput.focus(), 100);
            }
        }
    },

    /**
     * Close a modal
     * @param {string|HTMLElement} modalId - Modal element or ID
     * @param {Function} onCloseCallback - Optional callback after closing
     */
    close: function(modalId, onCloseCallback = null) {
        const modal = typeof modalId === 'string'
            ? document.getElementById(modalId)
            : modalId;

        if (!modal) {
            console.error('ModalManager.close: Modal not found', modalId);
            return;
        }

        modal.classList.add('hidden');
        modal.classList.remove('flex');

        // Run callback if provided
        if (typeof onCloseCallback === 'function') {
            onCloseCallback();
        }
    },

    /**
     * Toggle a modal (open if closed, close if open)
     * @param {string|HTMLElement} modalId - Modal element or ID
     */
    toggle: function(modalId) {
        const modal = typeof modalId === 'string'
            ? document.getElementById(modalId)
            : modalId;

        if (!modal) {
            console.error('ModalManager.toggle: Modal not found', modalId);
            return;
        }

        if (modal.classList.contains('hidden')) {
            this.open(modal);
        } else {
            this.close(modal);
        }
    },

    /**
     * Setup backdrop click to close
     * @param {string|HTMLElement} modalId - Modal element or ID
     */
    setupBackdropClose: function(modalId) {
        const modal = typeof modalId === 'string'
            ? document.getElementById(modalId)
            : modalId;

        if (!modal) {
            console.error('ModalManager.setupBackdropClose: Modal not found', modalId);
            return;
        }

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.close(modal);
            }
        });
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.ModalManager = ModalManager;
}
