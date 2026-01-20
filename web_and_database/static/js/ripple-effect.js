/**
 * Material Design Ripple Effect
 * Automatically applies to all buttons except excluded ones
 */

class RippleEffect {
    constructor() {
        this.excludedIds = ['sendChatBtn']; // Exclude chat send button
        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.attachRipples());
        } else {
            this.attachRipples();
        }
    }

    attachRipples() {
        // Select all buttons and links that look like buttons
        const selectors = [
            'button',
            'a.bg-blue-600',
            'a.bg-purple-600',
            'a.submit-btn',
            '.brightness-btn',
            '.preset-btn'
        ];

        const elements = document.querySelectorAll(selectors.join(', '));

        elements.forEach(element => {
            // Skip excluded buttons
            if (this.excludedIds.includes(element.id)) {
                return;
            }

            // Skip if already has ripple
            if (element.classList.contains('ripple-container')) {
                return;
            }

            // Add ripple container class
            element.classList.add('ripple-container');

            // Add click event listener
            element.addEventListener('click', (e) => this.createRipple(e, element));
        });
    }

    createRipple(event, element) {
        // Get element position and size
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);

        // Calculate click position relative to element
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;

        // Create ripple span
        const ripple = document.createElement('span');
        ripple.classList.add('ripple');
        ripple.style.width = ripple.style.height = `${size}px`;
        ripple.style.left = `${x}px`;
        ripple.style.top = `${y}px`;

        // Add to element
        element.appendChild(ripple);

        // Remove ripple after animation completes
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }
}

// Initialize ripple effect
new RippleEffect();
