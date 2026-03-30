# App.py Blueprint Refactoring Plan

## Current State
- **app.py**: 1529 lines (unmaintainable)
- **Routes**: 42 endpoints
- **Helpers**: 7 utility functions
- **Config**: Scattered throughout file

## Target Structure

```
web_and_database/
├── app.py                    # 70 lines - app factory + blueprint registration
├── config.py                 # 30 lines - configuration
├── utils/
│   ├── __init__.py
│   ├── decorators.py         # login_required, admin_required
│   ├── helpers.py            # is_quiet_hours, is_off_hours, convert_wind_direction
│   ├── mail.py               # send_reset_email
│   └── rate_limit.py         # check_location_change_limit, location_changes dict
├── blueprints/
│   ├── __init__.py
│   ├── landing.py            # 6 routes - /, /teaser, /waitlist, /privacy, static assets
│   ├── auth.py               # 6 routes - register, login, logout, forgot/reset password, test-reset-db
│   ├── dashboard.py          # 4 routes - dashboard, dashboard/<type>, themes, wifi-setup-guide
│   ├── api_user.py           # 5 routes - update location/threshold/wind/off-times/theme
│   ├── api_arduino.py        # 5 routes - arduino data, callback, discovery, status, error-reports
│   ├── api_chat.py           # 2 routes - /api/chat, /api/chat/status
│   ├── admin.py              # 5 routes - trigger-processor, waitlist, broadcast
│   └── reports.py            # 1 route - report-error
```

---

## Migration Map

### BLUEPRINT: landing.py (Lines 310-519)
**Routes:**
- `/` → index() - line 310-322
- `/styles.css` → landing_styles() - line 324-328
- `/images/<path:filename>` → landing_images() - line 330-335
- `/teaser` → teaser() - line 337-340
- `/waitlist` GET → waitlist_form() - line 342-346
- `/waitlist/submit` POST → waitlist_submit() - line 348-383
- `/privacy` → privacy() - line 516-519

**Dependencies:**
- `get_remote_address` (for IP tracking)
- `limiter` (rate limiting on submit)
- `waitlist_db` functions
- `SURF_LOCATIONS` constant

---

### BLUEPRINT: auth.py (Lines 403-651)
**Routes:**
- `/register` GET/POST → register() - line 521-589
- `/login` GET/POST → login() - line 591-641
- `/logout` → logout() - line 643-650
- `/forgot-password` GET/POST → forgot_password() - line 403-445
- `/reset-password/<token>` GET/POST → reset_password_form() - line 447-481
- `/test-reset-db` → test_reset_db() - line 483-514

**Dependencies:**
- `bcrypt` (password hashing)
- `limiter` (rate limiting)
- Forms: `RegistrationForm, LoginForm, ForgotPasswordForm, ResetPasswordForm`
- `send_reset_email()` helper
- DB models: `User, PasswordResetToken`
- `add_user_and_lamp()` from data_base
- `SURF_LOCATIONS` constant

---

### BLUEPRINT: dashboard.py (Lines 652-758, 1352-1399)
**Routes:**
- `/dashboard` → dashboard() - line 652-705
- `/dashboard/<view_type>` → dashboard_view() - line 707-757
- `/themes` → themes_page() - line 1352-1374
- `/wifi-setup-guide` → wifi_setup_guide() - line 1376-1399

**Dependencies:**
- `@login_required` decorator
- `get_user_lamp_data()` from data_base
- `SURF_LOCATIONS` constant
- `markdown` library (for wifi guide)
- Template rendering

---

### BLUEPRINT: api_user.py (Lines 759-906, 1401-1433)
**Routes:**
- `/update-location` POST → update_location() - line 759-792
- `/update-threshold` POST → update_threshold() - line 794-819
- `/update-wind-threshold` POST → update_wind_threshold() - line 821-846
- `/update-off-times` POST → update_off_times() - line 848-876
- `/update-theme` POST → update_theme() - line 878-906
- `/update-led-theme` POST → update_led_theme() - line 1401-1433

**Dependencies:**
- `@login_required` decorator
- `@limiter.limit()` (rate limiting)
- `check_location_change_limit()` helper
- DB models: `User`
- `SessionLocal` from data_base
- `update_user_location()` from data_base
- `SURF_LOCATIONS` constant

---

### BLUEPRINT: api_arduino.py (Lines 1117-1350)
**Routes:**
- `/api/arduino/callback` POST → handle_arduino_callback() - line 1117-1195
- `/api/arduino/<int:arduino_id>/data` GET → get_arduino_surf_data() - line 1197-1274
- `/api/discovery/server` GET → get_server_discovery() - line 1276-1302
- `/api/arduino/status` GET → arduino_status_overview() - line 1304-1350
- `/api/error-reports` GET → api_error_reports() - line 961-998

**Dependencies:**
- DB models: `Lamp, CurrentConditions, User, ErrorReport`
- `is_quiet_hours()` helper
- `is_off_hours()` helper
- `SessionLocal` from data_base

---

### BLUEPRINT: api_chat.py (Lines 1000-1091)
**Routes:**
- `/api/chat` POST → chat() - line 1000-1084
- `/api/chat/status` GET → chat_status() - line 1086-1091

**Dependencies:**
- `@login_required` decorator
- `genai` (Gemini AI)
- `CHAT_BOT_ENABLED, GEMINI_API_KEY, GEMINI_MODEL` config
- `build_chat_context()` from chat_logic
- DB models: `User, Lamp, CurrentConditions`

---

### BLUEPRINT: reports.py (Lines 908-959)
**Routes:**
- `/report-error` POST → report_error() - line 908-959

**Dependencies:**
- `@login_required` decorator
- `@limiter.limit()` (rate limiting)
- `get_user_lamp_data()` from data_base
- DB models: `ErrorReport`

---

### BLUEPRINT: admin.py (Lines 385-401, 1093-1115, 1439-1521)
**Routes:**
- `/admin/waitlist` → admin_waitlist() - line 385-401
- `/admin/trigger-processor` → trigger_processor() - line 1093-1115
- `/admin/broadcast` GET → admin_broadcast() - line 1439-1443
- `/admin/broadcast/create` POST → create_broadcast() - line 1445-1492
- `/api/broadcasts` GET → get_active_broadcasts() - line 1494-1521

**Dependencies:**
- `@login_required` decorator
- `@admin_required` decorator
- `@limiter.limit()` (rate limiting)
- `get_all_waitlist_entries, get_recent_signups, get_waitlist_count` from waitlist_db
- `sanitize_input` from forms
- DB models: `User, Broadcast`
- `SURF_LOCATIONS` constant
- Background processor import

---

## Utility Functions to Extract

### utils/helpers.py
- `is_quiet_hours()` - line 108-137
- `is_off_hours()` - line 139-171
- `convert_wind_direction()` - line 187-195

### utils/decorators.py
- `login_required()` - line 246-259
- `admin_required()` - line 261-284

### utils/rate_limit.py
- `check_location_change_limit()` - line 286-306
- `location_changes = {}` - line 104

### utils/mail.py
- `send_reset_email()` - line 214-244

---

## Configuration to Extract (config.py)

```python
# Lines 61-101, 175-183, 202-210
- SECRET_KEY, session config
- Security headers
- Bcrypt, Mail, Limiter initialization
- SURF_LOCATIONS constant
- Redis URL
- Gemini AI config
```

---

## New app.py Structure (70 lines)

```python
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from config import configure_app
from blueprints import (
    landing, auth, dashboard, api_user,
    api_arduino, api_chat, reports, admin
)

def create_app():
    app = Flask(__name__)

    # Configure app
    configure_app(app)

    # Fix for Render's reverse proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Register blueprints
    app.register_blueprint(landing.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(api_user.bp)
    app.register_blueprint(api_arduino.bp)
    app.register_blueprint(api_chat.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(admin.bp)

    return app

app = create_app()

if __name__ == '__main__':
    import os
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5001, debug=debug_mode)
```

---

## Import Dependencies Summary

**Per Blueprint:**
- All blueprints need: `Blueprint, request, jsonify, flash, redirect, url_for, render_template, session`
- Auth: `bcrypt, forms, limiter, mail, data_base models`
- Dashboard: `get_user_lamp_data, markdown, login_required`
- API User: `login_required, limiter, SessionLocal, User, check_location_change_limit`
- API Arduino: `SessionLocal, Lamp, CurrentConditions, User, ErrorReport, is_quiet_hours, is_off_hours`
- API Chat: `login_required, genai, chat_logic, User, Lamp, CurrentConditions`
- Reports: `login_required, limiter, get_user_lamp_data, ErrorReport`
- Admin: `login_required, admin_required, limiter, waitlist_db, forms, Broadcast`
- Landing: `limiter, send_from_directory, get_remote_address, waitlist_db`

---

## Shared Instances (passed via config.py)

- `bcrypt` → used in auth.py
- `limiter` → used in auth, landing, api_user, reports, admin
- `mail` → used in auth (send_reset_email)
- `SURF_LOCATIONS` → used in landing, auth, dashboard, api_user, admin

---

## Migration Steps

1. ✅ Create utils/ folder and extract helpers
2. ✅ Create config.py with app configuration
3. ✅ Create blueprints/ folder
4. ✅ Write each blueprint file (8 files)
5. ✅ Rewrite app.py to 70 lines
6. ✅ Test imports and routes
7. ✅ Verify no broken dependencies

---

## Token Estimate

- Write config.py: ~2k tokens
- Write utils/ (4 files): ~4k tokens
- Write blueprints/ (8 files): ~25k tokens
- Rewrite app.py: ~1k tokens
- Testing/fixes: ~5k tokens

**Total: ~37k tokens** (optimized from 55k)

---

## Risk Mitigation

**Potential Issues:**
1. Circular imports (blueprints importing utils, utils importing app)
   - **Solution**: Use lazy imports, pass instances via config
2. Session/limiter initialization order
   - **Solution**: Initialize in config.py, pass to blueprints via current_app
3. Missing imports in blueprints
   - **Solution**: Run test after each blueprint creation

**Testing Strategy:**
- After creating each blueprint, verify it imports successfully
- Test one route per blueprint before moving to next
- Keep old app.py as app_old.py until verification complete
