// Dashboard Initialization
// This file contains all initialization code for dashboard features

// Initialize feature handlers
function initDashboard(config) {
    // Location Update
    LocationUpdate.init(config.location);

    // Wave and Wind Thresholds
    WaveThreshold.init();
    WindThreshold.init();

    // Brightness Control
    BrightnessControl.init(config.brightnessLevel);

    // Quiet Hours
    QuietHours.init(config.quietTimesEnabled);

    // Unit Preference
    UnitPreference.init(config.preferredOutput);

    // Night Mode (Off Hours) - Preset & Custom Controls
    if (config.offHoursEnabled) {
        OffHours.init();
    }

    // LED Visualization
    LEDDataFetcher.init(config.arduinoId, config.theme);

    // Error Report Modal
    ErrorReport.init();

    // Chat Assistant
    ChatAssistant.init();

    // Broadcast Notifications
    Broadcasts.init();

    // Arduino Management (Link New Lamp)
    ArduinoManagement.init();

    // PWA Notifications
    Notifications.init();
}

// Underlayer Control Panel Configuration
window.underlayerConfig = {
    left: { xOffset: 0, yOffset: 0, opacity: 0.13, color: '#000000' },
    center: { xOffset: 0, yOffset: 0, opacity: 0.13, color: '#000000' },
    right: { xOffset: 0, yOffset: 0, opacity: 0.13, color: '#000000' }
};

function toggleUnderlayerPanel() {
    const panel = document.getElementById('underlayerControlPanel');
    const btn = document.getElementById('underlayerToggleBtn');
    panel.classList.toggle('hidden');
    btn.classList.toggle('hidden');
}

function setupUnderlayerControls() {
    const strips = ['left', 'center', 'right'];

    strips.forEach(strip => {
        // X Offset
        const xInput = document.getElementById(`${strip}X`);
        const xVal = document.getElementById(`${strip}XVal`);
        xInput.addEventListener('input', (e) => {
            window.underlayerConfig[strip].xOffset = parseFloat(e.target.value);
            xVal.textContent = e.target.value;
        });

        // Y Offset
        const yInput = document.getElementById(`${strip}Y`);
        const yVal = document.getElementById(`${strip}YVal`);
        yInput.addEventListener('input', (e) => {
            window.underlayerConfig[strip].yOffset = parseFloat(e.target.value);
            yVal.textContent = e.target.value;
        });

        // Opacity
        const opacityInput = document.getElementById(`${strip}Opacity`);
        const opacityVal = document.getElementById(`${strip}OpacityVal`);
        opacityInput.addEventListener('input', (e) => {
            window.underlayerConfig[strip].opacity = parseFloat(e.target.value);
            opacityVal.textContent = parseFloat(e.target.value).toFixed(2);
        });

        // Color
        const colorInput = document.getElementById(`${strip}Color`);
        colorInput.addEventListener('input', (e) => {
            window.underlayerConfig[strip].color = e.target.value;
        });
    });
}

function exportUnderlayerConfig() {
    const output = document.getElementById('configOutput');
    const config = JSON.stringify(window.underlayerConfig, null, 2);
    output.textContent = `// Underlayer Configuration:\n${config}`;
    output.classList.remove('hidden');
}

// Status Update Time Display
function formatTimeAgo(isoTimestamp) {
    const now = new Date();
    const updated = new Date(isoTimestamp);
    const diffMs = now - updated;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
}

function updateStatusTime() {
    const elem = document.getElementById('statusUpdateTime');
    if (elem?.dataset.timestamp) {
        elem.textContent = formatTimeAgo(elem.dataset.timestamp);
    }
}

// Check for pending theme update from themes page
function checkThemeUpdate() {
    const pendingThemeJson = localStorage.getItem('pendingThemeUpdate');
    if (pendingThemeJson) {
        try {
            const pendingTheme = JSON.parse(pendingThemeJson);

            // Update theme name display immediately
            const themeNameElement = document.getElementById('currentThemeName');
            if (themeNameElement) {
                themeNameElement.textContent = pendingTheme.name;
            }

            // Update LED visualization colors on next animation frame (syncs with animation loop)
            requestAnimationFrame(() => {
                if (window.LEDDataFetcher) {
                    LEDDataFetcher.updateTheme(pendingTheme.id);
                }
            });

            // Clear the pending update (non-blocking)
            localStorage.removeItem('pendingThemeUpdate');
        } catch (e) {
            console.error('Failed to parse theme update:', e);
            localStorage.removeItem('pendingThemeUpdate');
        }
    }
}

// Initialize everything when DOM is ready
setupUnderlayerControls();

// Update status time on page load and every minute
updateStatusTime();
setInterval(updateStatusTime, 60000);

// Check for theme updates
checkThemeUpdate();
