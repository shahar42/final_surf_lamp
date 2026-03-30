/**
 * Flash Message Auto-Dismiss
 * Handles automatic dismissal of flash messages with configurable timing
 */

const FLASH_TIMINGS = {
    'short': 3000,      // 3 seconds
    'medium': 15000,    // 15 seconds
    'default': 7000     // 7 seconds
};

document.addEventListener('DOMContentLoaded', () => {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(flashMsg => {
        const timing = flashMsg.dataset.timing || 'default';
        const duration = FLASH_TIMINGS[timing] || FLASH_TIMINGS['default'];

        setTimeout(() => {
            flashMsg.style.transition = 'opacity 0.5s ease-out';
            flashMsg.style.opacity = '0';
            setTimeout(() => flashMsg.remove(), 500);
        }, duration);
    });
});
