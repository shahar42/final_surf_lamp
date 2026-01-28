/**
 * Mobile Bottom Tab Navigation
 * Handles tab switching with smooth animations
 */
const MobileTabs = (function() {
    let currentTab = 'lamp';
    let tabOrder = ['lamp', 'surf', 'location', 'light', 'more'];

    function init() {
        // Only initialize on mobile (< 1024px)
        if (window.innerWidth >= 1024) {
            showAllPanelsDesktop();
            return;
        }

        const tabs = document.querySelectorAll('.mobile-tab');
        const panels = document.querySelectorAll('.tab-panel');

        // Set initial state
        setActiveTab('lamp');

        // Add click handlers to tabs
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;
                switchTab(tabName);
            });
        });

        // Handle resize - show all panels on desktop
        window.addEventListener('resize', debounce(() => {
            if (window.innerWidth >= 1024) {
                showAllPanelsDesktop();
            } else {
                // Re-apply current tab on mobile
                setActiveTab(currentTab);
            }
        }, 150));

        // Handle swipe gestures (optional enhancement)
        setupSwipeGestures();

        // Sync mobile elements with desktop functionality
        setupMobileElementSync();
    }

    /**
     * Sync mobile-specific elements with the main functionality
     */
    function setupMobileElementSync() {
        // Location select sync
        const mobileLocationSelect = document.getElementById('locationSelectMobile');
        const desktopLocationSelect = document.getElementById('locationSelect');

        if (mobileLocationSelect && desktopLocationSelect) {
            mobileLocationSelect.addEventListener('change', (e) => {
                desktopLocationSelect.value = e.target.value;
                desktopLocationSelect.dispatchEvent(new Event('change'));
            });
        }

        // Unit toggle sync
        const mobileUnitToggle = document.getElementById('unitToggleMobile');
        const desktopUnitToggle = document.getElementById('unitToggle');

        if (mobileUnitToggle && desktopUnitToggle) {
            mobileUnitToggle.addEventListener('click', () => {
                desktopUnitToggle.click();
                // Sync button text after a short delay
                setTimeout(() => {
                    mobileUnitToggle.textContent = desktopUnitToggle.textContent;
                }, 100);
            });
        }

        // Quiet hours toggle sync
        const mobileQuietToggle = document.getElementById('quietHoursToggleMobile');
        const desktopQuietToggle = document.getElementById('quietHoursToggle');

        if (mobileQuietToggle && desktopQuietToggle) {
            mobileQuietToggle.addEventListener('click', () => {
                desktopQuietToggle.click();
                // Sync button state after a short delay
                setTimeout(() => {
                    syncButtonState(mobileQuietToggle, desktopQuietToggle);
                }, 100);
            });
        }

        // Error report button sync
        const mobileReportBtn = document.getElementById('reportErrorBtnMobile');
        const desktopReportBtn = document.getElementById('reportErrorBtn');

        if (mobileReportBtn && desktopReportBtn) {
            mobileReportBtn.addEventListener('click', () => {
                desktopReportBtn.click();
            });
        }

        // Arduino management sync
        setupArduinoManagementSync();
    }

    /**
     * Sync button visual state
     */
    function syncButtonState(target, source) {
        target.className = source.className;
        target.textContent = source.textContent;
    }

    /**
     * Setup Arduino management sync between mobile and desktop
     */
    function setupArduinoManagementSync() {
        const showBtnMobile = document.getElementById('showAddArduinoBtnMobile');
        const formMobile = document.getElementById('addArduinoFormMobile');
        const cancelMobile = document.getElementById('cancelAddArduinoMobile');
        const submitMobile = document.getElementById('submitAddArduinoMobile');

        if (showBtnMobile && formMobile) {
            showBtnMobile.addEventListener('click', () => {
                formMobile.classList.toggle('hidden');
            });

            if (cancelMobile) {
                cancelMobile.addEventListener('click', () => {
                    formMobile.classList.add('hidden');
                });
            }

            if (submitMobile) {
                submitMobile.addEventListener('click', async () => {
                    const arduinoId = document.getElementById('newArduinoIdMobile').value;
                    const location = document.getElementById('newArduinoLocationMobile').value;

                    if (!arduinoId) {
                        alert('Please enter an Arduino ID');
                        return;
                    }

                    try {
                        const response = await fetch('/api/arduino/link', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ arduino_id: arduinoId, location: location })
                        });

                        const data = await response.json();

                        if (response.ok) {
                            window.location.reload();
                        } else {
                            alert(data.error || 'Failed to link Arduino');
                        }
                    } catch (error) {
                        alert('Network error. Please try again.');
                    }
                });
            }
        }
    }

    function switchTab(tabName) {
        if (tabName === currentTab) return;

        const prevIndex = tabOrder.indexOf(currentTab);
        const newIndex = tabOrder.indexOf(tabName);
        const direction = newIndex > prevIndex ? 'left' : 'right';

        // Animate out current panel
        const currentPanel = document.querySelector(`.tab-panel[data-tab="${currentTab}"]`);
        if (currentPanel) {
            currentPanel.classList.remove('active');
        }

        // Update current tab
        currentTab = tabName;

        // Animate in new panel with direction
        setActiveTab(tabName, direction);

        // Haptic feedback on supported devices
        if (navigator.vibrate) {
            navigator.vibrate(10);
        }
    }

    function setActiveTab(tabName, direction = null) {
        // Update tab buttons
        document.querySelectorAll('.mobile-tab').forEach(tab => {
            if (tab.dataset.tab === tabName) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        // Update panels
        document.querySelectorAll('.tab-panel').forEach(panel => {
            if (panel.dataset.tab === tabName) {
                panel.classList.add('active');

                // Add directional animation class
                if (direction) {
                    panel.classList.remove('tab-slide-left', 'tab-slide-right');
                    panel.classList.add(direction === 'left' ? 'tab-slide-left' : 'tab-slide-right');

                    // Remove animation class after animation completes
                    setTimeout(() => {
                        panel.classList.remove('tab-slide-left', 'tab-slide-right');
                    }, 250);
                }
            } else {
                panel.classList.remove('active');
            }
        });

        currentTab = tabName;
    }

    function showAllPanelsDesktop() {
        // On desktop, show all panels (no tabs)
        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.add('active');
            panel.style.display = '';
        });
    }

    function setupSwipeGestures() {
        const container = document.body;
        let touchStartX = 0;
        let touchEndX = 0;
        const minSwipeDistance = 50;

        container.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
        }, { passive: true });

        container.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        }, { passive: true });

        function handleSwipe() {
            const distance = touchEndX - touchStartX;

            if (Math.abs(distance) < minSwipeDistance) return;

            const currentIndex = tabOrder.indexOf(currentTab);

            if (distance < 0 && currentIndex < tabOrder.length - 1) {
                // Swipe left -> next tab
                switchTab(tabOrder[currentIndex + 1]);
            } else if (distance > 0 && currentIndex > 0) {
                // Swipe right -> previous tab
                switchTab(tabOrder[currentIndex - 1]);
            }
        }
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Public API
    return {
        init,
        switchTab,
        getCurrentTab: () => currentTab
    };
})();

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    MobileTabs.init();
});
