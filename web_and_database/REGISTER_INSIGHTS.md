# Registration Page Insights

## Bugs

### 1. Eye icon shrinks on desktop
`w-5 h-5 md:w-2.5 md:h-2.5` — the `md:` breakpoint makes the password toggle icon 10px on desktop (half the mobile size). Likely should be `md:w-5 md:h-5` or just `w-5 h-5` without a breakpoint override.

## High Impact

### 2. DRY violation — three identical validation handlers
Lines 254-322 contain three copy-pasted input validation blocks (name, email, password). Each follows the same pattern:
1. Get field element
2. Listen to `input` event
3. Test against a regex
4. Toggle `error`/`success` CSS classes

**Fix:** One reusable function:
```js
function validateField(id, regex) {
    const field = document.getElementById(id);
    if (!field) return;
    field.addEventListener('input', function() {
        const valid = regex.test(this.value);
        this.classList.toggle('success', valid);
        this.classList.toggle('error', !valid && this.value.length > 0);
    });
}

validateField('name', /^[a-zA-Z0-9\s\-']{2,50}$/);
validateField('email', /^[^\s@]+@[^\s@]+\.[^\s@]+$/);
validateField('password', /^.{8,128}$/);
```

### 3. Inline CSS — extract to `css/register.css`
72 lines of `<style>` in the HTML. Not cacheable by the browser, and mixes concerns.
Move to `static/css/register.css` and link it.

### 4. Unnecessary `dashboard.css` import
Line 27 loads the full dashboard stylesheet on the registration page.
The register page only needs `base.css` and its own styles — loading `dashboard.css` adds unused CSS.

## Already Good
- `<option>` elements explicitly styled (prevents invisible text on dark backgrounds)
- Server-side validation errors displayed per field with clear formatting
- Real-time client-side feedback (success/error borders)
- Password visibility toggle with clear SVG icons
- Privacy policy link with lock icon
- QR code required notice with conditional rendering
- Form uses CSRF protection via `form.hidden_tag()`
