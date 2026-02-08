# Dashboard Optimization Insights

## High Impact

### 1. Script Loading — Add `defer` to all `<script>` tags
Currently 20+ JS files load synchronously, each blocking HTML parsing until downloaded and executed.
Adding `defer` lets the browser download all scripts in parallel while parsing HTML, then execute them in order after the DOM is ready.

**Before:** Each script blocks rendering sequentially
**After:** All scripts download in parallel, execute after DOM parse
**Risk:** None — `defer` preserves execution order
**Effort:** Find-and-replace in `dashboard.html`

### 2. Tailwind CDN — Replace with purged build
`cdn.tailwindcss.com` ships the entire Tailwind library (~300KB uncompressed).
A build step with `npx tailwindcss -o dashboard.min.css --minify` scans actual class usage and outputs only what's needed (~10-15KB).

**Savings:** ~285KB per page load
**Effort:** Medium — requires adding a build step
**Trade-off:** Adds a build dependency, but eliminates runtime CSS compilation

### 3. Inline JS — Extract to cacheable file
The ~140-line inline `<script>` block (init code, underlayer controls, theme updates) runs on every page load and cannot be cached by the browser.

**Fix:** Extract to `static/js/dashboard-init.js`
**Benefit:** Cached after first visit, reduces HTML payload

## Low Impact

### 4. iOS Splash Screens
Nine `<link>` tags for splash screens (lines 26-55). Only one matches per device. No performance cost — just visual noise in the HTML. Could be moved to a partial (`partials/ios_splash.html`) for cleanliness.

### 5. External CDN Dependencies
- noUiSlider CSS + JS from `cdnjs.cloudflare.com`
- Google Fonts from `fonts.googleapis.com`

Each external CDN adds a DNS lookup + connection. Self-hosting these would eliminate external dependencies and improve reliability, but the gain is marginal for a small user base.

## Already Good
- **Partial templates** — Clean separation via `{% include %}`, easy to maintain
- **Font loading** — `display=swap` parameter prevents invisible text during load
- **PWA configuration** — Manifest, touch icons, and meta tags properly set up
- **Feature isolation** — One JS file per feature, clear naming conventions
- **CSS architecture** — Separated into `base.css`, `dashboard.css`, and feature-specific files
