/**
 * Theme Color Sync
 * Automatically syncs PWA status bar color with CSS background gradient
 * Any change to --gradient-start in base.css automatically updates the status bar
 */

(function() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', syncThemeColor);
    } else {
        syncThemeColor();
    }

    function syncThemeColor() {
        // Get the gradient-start color from CSS variables
        const gradientStart = getComputedStyle(document.documentElement)
            .getPropertyValue('--gradient-start')
            .trim();

        if (!gradientStart) {
            console.warn('ThemeColorSync: --gradient-start CSS variable not found');
            return;
        }

        // Update all theme-color meta tags
        const themeColorMeta = document.querySelector('meta[name="theme-color"]');
        const tileColorMeta = document.querySelector('meta[name="msapplication-TileColor"]');

        if (themeColorMeta) {
            themeColorMeta.setAttribute('content', gradientStart);
        }

        if (tileColorMeta) {
            tileColorMeta.setAttribute('content', gradientStart);
        }

        console.log('ThemeColorSync: Status bar color synced to', gradientStart);
    }
})();
