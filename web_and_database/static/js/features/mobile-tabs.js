/**
 * Mobile Bottom Tab Navigation
 *
 * SINGLE DOM APPROACH:
 * - Same elements for mobile and desktop (no duplicate IDs)
 * - Desktop: CSS shows all .dashboard-section
 * - Mobile: JS toggles .tab-active class on .dashboard-section[data-tab]
 */
const MobileTabs = (function() {
    let currentTab = 'lamp';
    const tabOrder = ['lamp', 'location', 'light', 'more'];

    function init() {
        // Only initialize tab behavior on mobile
        if (window.innerWidth >= 1024) return;

        // Set initial active tab
        setActiveTab('lamp');

        // Tab click handlers
        document.querySelectorAll('.mobile-tab').forEach(tab => {
            tab.addEventListener('click', () => switchTab(tab.dataset.tab));
        });

        // Handle viewport resize
        window.addEventListener('resize', debounce(() => {
            if (window.innerWidth >= 1024) {
                // Desktop: remove all tab-active classes (CSS shows all)
                document.querySelectorAll('.dashboard-section').forEach(s => {
                    s.classList.remove('tab-active', 'tab-slide-left', 'tab-slide-right');
                });
            } else {
                // Mobile: ensure current tab is active
                setActiveTab(currentTab);
            }
        }, 150));

        // Swipe gestures
        setupSwipeGestures();
    }

    function switchTab(tabName) {
        if (tabName === currentTab) return;

        const prevIndex = tabOrder.indexOf(currentTab);
        const newIndex = tabOrder.indexOf(tabName);
        const direction = newIndex > prevIndex ? 'next' : 'prev';

        // 1. Set Transition Direction for CSS
        document.documentElement.dataset.transition = direction;

        // 2. Perform Transition
        if (document.startViewTransition) {
            document.startViewTransition(() => {
                updateDOM(tabName);
            });
        } else {
            // Fallback for older browsers (instant switch)
            updateDOM(tabName);
        }

        // Haptic feedback
        if (navigator.vibrate) navigator.vibrate(10);
    }

    function updateDOM(tabName) {
        currentTab = tabName;
        
        // Update tab buttons
        document.querySelectorAll('.mobile-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // Update sections
        document.querySelectorAll('.dashboard-section[data-tab]').forEach(section => {
            section.classList.toggle('tab-active', section.dataset.tab === tabName);
        });
    }

    // Helper for initial load & resize
    function setActiveTab(tabName) {
        updateDOM(tabName);
    }

    function setupSwipeGestures() {
        let startX = 0;
        let touchedSlider = false;
        const minDistance = 50;

        document.body.addEventListener('touchstart', e => {
            startX = e.changedTouches[0].screenX;
            touchedSlider = !!e.target.closest('.noUi-target');
        }, { passive: true, capture: true });

        document.body.addEventListener('touchend', e => {
            if (touchedSlider) return;
            const distance = e.changedTouches[0].screenX - startX;
            if (Math.abs(distance) < minDistance) return;

            const idx = tabOrder.indexOf(currentTab);
            if (distance < 0 && idx < tabOrder.length - 1) {
                switchTab(tabOrder[idx + 1]);
            } else if (distance > 0 && idx > 0) {
                switchTab(tabOrder[idx - 1]);
            }
        }, { passive: true });
    }

    function debounce(fn, wait) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn(...args), wait);
        };
    }

    return { init, switchTab, getCurrentTab: () => currentTab };
})();

document.addEventListener('DOMContentLoaded', MobileTabs.init);
