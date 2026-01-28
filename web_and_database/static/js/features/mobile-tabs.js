/**
 * Mobile Bottom Tab Navigation
 * Handles tab switching with smooth animations
 *
 * SMART APPROACH: Reuses existing partials via CSS overrides.
 * No element duplication, no syncing needed.
 */
const MobileTabs = (function() {
    let currentTab = 'lamp';
    const tabOrder = ['lamp', 'surf', 'location', 'light', 'more'];

    function init() {
        // Only initialize on mobile (< 1024px)
        if (window.innerWidth >= 1024) {
            showAllPanelsDesktop();
            return;
        }

        // Set initial state
        setActiveTab('lamp');

        // Add click handlers to tabs
        document.querySelectorAll('.mobile-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                switchTab(tab.dataset.tab);
            });
        });

        // Handle resize - show all panels on desktop
        window.addEventListener('resize', debounce(() => {
            if (window.innerWidth >= 1024) {
                showAllPanelsDesktop();
            } else {
                setActiveTab(currentTab);
            }
        }, 150));

        // Swipe gestures for tab navigation
        setupSwipeGestures();
    }

    function switchTab(tabName) {
        if (tabName === currentTab) return;

        const prevIndex = tabOrder.indexOf(currentTab);
        const newIndex = tabOrder.indexOf(tabName);
        const direction = newIndex > prevIndex ? 'left' : 'right';

        currentTab = tabName;
        setActiveTab(tabName, direction);

        // Haptic feedback on supported devices
        if (navigator.vibrate) {
            navigator.vibrate(10);
        }
    }

    function setActiveTab(tabName, direction = null) {
        // Update tab buttons
        document.querySelectorAll('.mobile-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // Update panels
        document.querySelectorAll('.tab-panel').forEach(panel => {
            const isActive = panel.dataset.tab === tabName;
            panel.classList.toggle('active', isActive);

            if (isActive && direction) {
                panel.classList.remove('tab-slide-left', 'tab-slide-right');
                panel.classList.add(direction === 'left' ? 'tab-slide-left' : 'tab-slide-right');
                setTimeout(() => {
                    panel.classList.remove('tab-slide-left', 'tab-slide-right');
                }, 250);
            }
        });

        currentTab = tabName;
    }

    function showAllPanelsDesktop() {
        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.add('active');
        });
    }

    function setupSwipeGestures() {
        let touchStartX = 0;
        const minSwipeDistance = 50;

        document.body.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
        }, { passive: true });

        document.body.addEventListener('touchend', (e) => {
            const distance = e.changedTouches[0].screenX - touchStartX;
            if (Math.abs(distance) < minSwipeDistance) return;

            const currentIndex = tabOrder.indexOf(currentTab);
            if (distance < 0 && currentIndex < tabOrder.length - 1) {
                switchTab(tabOrder[currentIndex + 1]);
            } else if (distance > 0 && currentIndex > 0) {
                switchTab(tabOrder[currentIndex - 1]);
            }
        }, { passive: true });
    }

    function debounce(func, wait) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func(...args), wait);
        };
    }

    return {
        init,
        switchTab,
        getCurrentTab: () => currentTab
    };
})();

document.addEventListener('DOMContentLoaded', MobileTabs.init);
