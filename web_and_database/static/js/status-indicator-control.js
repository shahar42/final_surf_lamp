/**
 * Status Indicator Control Panel
 * Development tool to adjust positioning of sleep mode status indicator
 */

function toggleStatusIndicatorPanel() {
    const panel = document.getElementById('statusIndicatorControlPanel');
    const btn = document.getElementById('statusIndicatorToggleBtn');
    panel.classList.toggle('hidden');
    btn.classList.toggle('hidden');
}

function setupStatusIndicatorControls() {
    const statusIndicator = document.getElementById('sleepModeStatus');

    if (!statusIndicator) {
        console.warn('Status indicator not found');
        return;
    }

    // Top offset
    const topInput = document.getElementById('statusTop');
    const topVal = document.getElementById('statusTopVal');
    topInput.addEventListener('input', (e) => {
        const offset = parseFloat(e.target.value);
        statusIndicator.style.marginTop = `${offset}px`;
        topVal.textContent = offset;
    });

    // Right offset
    const rightInput = document.getElementById('statusRight');
    const rightVal = document.getElementById('statusRightVal');
    rightInput.addEventListener('input', (e) => {
        const offset = parseFloat(e.target.value);
        statusIndicator.style.marginRight = `${offset}px`;
        rightVal.textContent = offset;
    });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupStatusIndicatorControls);
} else {
    setupStatusIndicatorControls();
}
