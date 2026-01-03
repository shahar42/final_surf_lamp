/**
 * Broadcast Notifications
 * Handles loading and displaying admin broadcast messages
 */

const Broadcasts = {
    // State
    container: null,
    loadInterval: null,

    /**
     * Initialize broadcasts
     */
    init: function() {
        this.container = document.getElementById('broadcastContainer');

        if (!this.container) {
            console.warn('Broadcast container not found');
            return;
        }

        // Initial load
        this.loadBroadcasts();

        // Refresh every 5 minutes
        this.loadInterval = setInterval(
            () => this.loadBroadcasts(),
            DashboardConfig.INTERVALS.BROADCAST_CHECK
        );
    },

    /**
     * Fetch and display broadcasts from API
     */
    loadBroadcasts: async function() {
        try {
            const response = await fetch(DashboardConfig.API.BROADCASTS);
            const data = await response.json();

            // Clear existing broadcasts
            this.container.innerHTML = '';

            // Add each broadcast
            data.broadcasts.forEach(broadcast => {
                this.addBroadcast(broadcast);
            });
        } catch (error) {
            console.error('Failed to load broadcasts:', error);
        }
    },

    /**
     * Add a single broadcast to the container
     * @param {object} broadcast - Broadcast object with message property
     */
    addBroadcast: function(broadcast) {
        const bubble = document.createElement('div');
        bubble.className = 'bg-gradient-to-r from-yellow-400 to-orange-500 text-gray-900 rounded-2xl p-4 shadow-2xl relative animate-slide-in';

        // Create close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'absolute top-2 right-2 text-gray-700 hover:text-gray-900';
        closeBtn.onclick = () => bubble.remove();
        closeBtn.innerHTML = `
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
        `;

        // Create message content
        const content = document.createElement('div');
        content.className = 'pr-6';
        content.innerHTML = `
            <div class="font-bold text-sm mb-1">📢 Message from Surf Lamp</div>
            <div class="text-sm">${this.escapeHtml(broadcast.message)}</div>
        `;

        bubble.appendChild(closeBtn);
        bubble.appendChild(content);
        this.container.appendChild(bubble);
    },

    /**
     * Escape HTML to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml: function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Stop broadcast updates (cleanup)
     */
    destroy: function() {
        if (this.loadInterval) {
            clearInterval(this.loadInterval);
            this.loadInterval = null;
        }
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.Broadcasts = Broadcasts;
}
