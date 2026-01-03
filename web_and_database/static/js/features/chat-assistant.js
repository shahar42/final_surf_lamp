/**
 * Chat Assistant
 * Handles AI chatbot functionality (disabled in production due to memory constraints)
 */

const ChatAssistant = {
    // DOM elements
    chatFloatingBtn: null,
    chatModal: null,
    closeChatBtn: null,
    chatInput: null,
    sendChatBtn: null,
    chatMessages: null,

    /**
     * Initialize chat assistant
     */
    init: function() {
        // Get DOM elements
        this.chatFloatingBtn = document.getElementById('chatFloatingBtn');
        this.chatModal = document.getElementById('chatModal');
        this.closeChatBtn = document.getElementById('closeChatBtn');
        this.chatInput = document.getElementById('chatInput');
        this.sendChatBtn = document.getElementById('sendChatBtn');
        this.chatMessages = document.getElementById('chatMessages');

        if (!this.chatFloatingBtn || !this.chatModal) {
            console.log('Chat assistant elements not found');
            return;
        }

        // Check if chat feature is enabled
        this.checkChatStatus();

        // Setup event listeners
        this.setupEventListeners();
    },

    /**
     * Check if chat feature is enabled on server
     */
    checkChatStatus: async function() {
        try {
            const response = await fetch(DashboardConfig.API.CHAT_STATUS);
            const data = await response.json();

            if (data.enabled) {
                this.chatFloatingBtn.classList.remove('hidden');
            }
        } catch (err) {
            console.log('Chat feature not available');
        }
    },

    /**
     * Setup event listeners
     */
    setupEventListeners: function() {
        // Open chat modal
        this.chatFloatingBtn.addEventListener('click', () => this.openChat());

        // Close chat modal
        this.closeChatBtn.addEventListener('click', () => this.closeChat());

        // Close on backdrop click
        this.chatModal.addEventListener('click', (e) => {
            if (e.target === this.chatModal) {
                this.closeChat();
            }
        });

        // Send on button click
        this.sendChatBtn.addEventListener('click', () => this.sendMessage());

        // Send on Enter key (Shift+Enter for new line)
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    },

    /**
     * Open chat modal
     */
    openChat: function() {
        ModalManager.open('chatModal', this.chatInput);
    },

    /**
     * Close chat modal
     */
    closeChat: function() {
        ModalManager.close('chatModal');
    },

    /**
     * Add message to chat window
     * @param {string} text - Message text
     * @param {boolean} isUser - Whether message is from user (vs bot)
     */
    addMessage: function(text, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `flex items-start space-x-2 ${isUser ? 'justify-end' : ''}`;

        const bubble = document.createElement('div');
        bubble.className = `rounded-2xl px-4 py-2 max-w-xs ${isUser ? 'bg-blue-500 text-white' : 'bg-blue-100 text-gray-800'}`;

        const p = document.createElement('p');
        p.className = 'text-sm whitespace-pre-wrap';
        p.textContent = text;

        bubble.appendChild(p);
        messageDiv.appendChild(bubble);
        this.chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    },

    /**
     * Add loading indicator (three bouncing dots)
     */
    addLoadingIndicator: function() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'flex items-start space-x-2';
        loadingDiv.id = 'loadingIndicator';

        const bubble = document.createElement('div');
        bubble.className = 'bg-blue-100 text-gray-800 rounded-2xl px-4 py-2';
        bubble.innerHTML = '<div class="flex space-x-1"><div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div><div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></div><div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div></div>';

        loadingDiv.appendChild(bubble);
        this.chatMessages.appendChild(loadingDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    },

    /**
     * Remove loading indicator
     */
    removeLoadingIndicator: function() {
        const loading = document.getElementById('loadingIndicator');
        if (loading) loading.remove();
    },

    /**
     * Send message to chat API
     */
    sendMessage: async function() {
        const message = this.chatInput.value.trim();
        if (!message) return;

        // Add user message
        this.addMessage(message, true);
        this.chatInput.value = '';

        // Disable input while processing
        this.chatInput.disabled = true;
        this.sendChatBtn.disabled = true;
        this.addLoadingIndicator();

        try {
            const result = await ApiClient.post(DashboardConfig.API.CHAT, {
                message: message
            });

            this.removeLoadingIndicator();

            if (result.ok && result.data.success) {
                this.addMessage(result.data.response, false);
            } else {
                this.addMessage(result.data.error || 'Sorry, I encountered an error. Please try again.', false);
            }
        } catch (error) {
            this.removeLoadingIndicator();
            this.addMessage('Network error. Please check your connection and try again.', false);
        } finally {
            this.chatInput.disabled = false;
            this.sendChatBtn.disabled = false;
            this.chatInput.focus();
        }
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.ChatAssistant = ChatAssistant;
}
