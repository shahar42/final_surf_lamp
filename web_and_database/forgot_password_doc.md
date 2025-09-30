# Forgot Password System - Technical Documentation

## Overview
Complete password reset flow using secure token-based authentication with email delivery via Brevo SMTP.

---

## Architecture Components

### 1. Database Schema
**Table:** `password_reset_tokens`
```sql
CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    token_hash VARCHAR(64) NOT NULL,  -- SHA256 hash of the token
    expiration_time TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    is_invalidated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2. Email Configuration (Brevo SMTP)
**Environment Variables Required:**
```bash
MAIL_SERVER=smtp-relay.brevo.com
MAIL_PORT=587
MAIL_USERNAME=956602001@smtp-brevo.com
MAIL_PASSWORD=KNjkEZUItwaAP9hq
MAIL_DEFAULT_SENDER=shaharisn1@gmail.com  # MUST be verified in Brevo dashboard
```

**Critical:** `MAIL_DEFAULT_SENDER` must be verified in Brevo (Settings → Senders & IP → Add and verify sender). Using unverified senders causes "Error: sender not valid" rejections.

**Flask-Mail Configuration:**
```python
app.config.update(
    MAIL_SERVER=os.environ.get('MAIL_SERVER'),
    MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER')
)
mail = Mail(app)
```

---

## Password Reset Flow

### Step 1: Request Password Reset
**Route:** `/forgot-password` (GET, POST)
**File:** `web_and_database/app.py:274-316`

**Rate Limiting:** 5 requests per hour per IP (via Flask-Limiter)

**Process:**
1. User submits email address via `ForgotPasswordForm`
2. Email normalized to lowercase
3. Database lookup for user with matching email
4. **Security:** Always shows same success message regardless of whether user exists (prevents email enumeration)

**If user exists:**
```python
# Generate cryptographically secure 48-byte token (URL-safe)
token = secrets.token_urlsafe(48)  # ~64 characters

# Hash token with SHA256 for database storage
token_hash = hashlib.sha256(token.encode()).hexdigest()

# Set 20-minute expiration
expiration = datetime.utcnow() + timedelta(minutes=20)

# Invalidate all previous unused tokens for this user
db.query(PasswordResetToken).filter(
    PasswordResetToken.user_id == user.user_id,
    PasswordResetToken.used_at.is_(None)
).update({"is_invalidated": True})

# Create new token record
reset_token = PasswordResetToken(
    user_id=user.user_id,
    token_hash=token_hash,
    expiration_time=expiration
)
db.add(reset_token)
db.commit()

# Send reset email with plaintext token (only time it's visible)
send_reset_email(user.email, user.username, token)
```

**User sees:** `"If an account exists with that email, a reset link has been sent."`

### Step 2: Email Delivery
**Function:** `send_reset_email(user_email, username, token)`
**File:** `web_and_database/app.py:164-191`

**Email Construction:**
```python
reset_link = url_for('reset_password_form', token=token, _external=True)
# Example: https://final-surf-lamp-web.onrender.com/reset-password/<token>

msg = Message(
    subject="Password Reset Request",
    sender=("Surf Lamp", app.config.get('MAIL_DEFAULT_SENDER')),
    recipients=[user_email]
)

msg.body = f"""Hello {username},

Click this link to reset your password:
{reset_link}

This link expires in 20 minutes.
If you didn't request this, ignore this email.

---
Surf Lamp Team
"""
```

**Email Delivery Chain:**
1. Flask-Mail → Brevo SMTP (`smtp-relay.brevo.com:587`)
2. Brevo validates sender → Sends via shared IP
3. Gmail/recipient server receives → Spam filtering
4. User inbox delivery

**Brevo Dashboard Tracking:**
- **Sent:** Email left Brevo servers
- **Delivered:** Recipient server accepted email
- **Error:** Sender not verified or other SMTP issue

### Step 3: Reset Password Form
**Route:** `/reset-password/<token>` (GET, POST)
**File:** `web_and_database/app.py:318-352`

**Token Validation Process:**
```python
# Hash the URL token to match database
token_hash = hashlib.sha256(token.encode()).hexdigest()

# Find valid token in database
reset_token = db.query(PasswordResetToken).filter(
    PasswordResetToken.token_hash == token_hash,
    PasswordResetToken.expiration_time > datetime.utcnow(),  # Not expired
    PasswordResetToken.used_at.is_(None),                    # Not used
    PasswordResetToken.is_invalidated == False               # Not invalidated
).first()

if not reset_token:
    flash('Invalid or expired reset link', 'error')
    return redirect(url_for('login'))
```

**Password Update:**
```python
# Get user from token
user = db.query(User).filter(User.user_id == reset_token.user_id).first()

# Hash new password with bcrypt
new_password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

# Update password
user.password_hash = new_password_hash

# Mark token as used
reset_token.used_at = datetime.utcnow()

db.commit()

flash('Password reset successful! Please log in.', 'success')
return redirect(url_for('login'))
```

---

## Security Measures

### 1. **Token Security**
- **Generation:** `secrets.token_urlsafe(48)` - cryptographically secure random token
- **Storage:** Only SHA256 hash stored in database, never plaintext token
- **Single Use:** Token marked as `used_at` timestamp after successful reset
- **Expiration:** 20-minute validity window
- **Invalidation:** All previous unused tokens invalidated when new request made

### 2. **Email Enumeration Prevention**
- Same success message shown whether email exists or not
- Prevents attackers from discovering valid email addresses

### 3. **Rate Limiting**
- 5 password reset requests per hour per IP address
- Prevents brute force attacks and email bombing

### 4. **Password Hashing**
- Bcrypt with automatic salt generation
- Work factor handled by Flask-Bcrypt defaults

### 5. **Token Transmission**
- Token only appears in URL (HTTPS encrypted)
- Token never logged or stored in plaintext
- Email body contains full reset URL

---

## Common Issues & Solutions

### Issue 1: "Sender not valid" Error in Brevo
**Symptom:** Emails show "Error" status in Brevo dashboard
**Cause:** `MAIL_DEFAULT_SENDER` not verified in Brevo
**Solution:**
1. Go to Brevo Dashboard → Senders & IP → Senders
2. Add sender email address
3. Verify via confirmation email
4. Update `MAIL_DEFAULT_SENDER` environment variable
5. Redeploy application

### Issue 2: Email Delivered but Not in Inbox
**Symptom:** Brevo shows "Delivered" but user doesn't see email
**Cause:** Gmail/provider spam filtering
**Solution:**
1. Check spam/junk folder
2. Check Gmail Promotions tab
3. Search: `in:anywhere from:brevosend.com`
4. For production: Set up custom domain with DKIM/DMARC authentication

### Issue 3: Token Expired or Invalid
**Symptom:** "Invalid or expired reset link" message
**Causes:**
- More than 20 minutes passed since request
- Token already used
- New password reset request invalidated old token
- User manually edited token URL

**Solution:** Request new password reset

### Issue 4: Email Configuration Not Loading
**Symptom:** `MAIL_SERVER: None` in logs
**Cause:** Environment variables not set in production
**Solution:**
1. Verify all `MAIL_*` variables in Render dashboard (Settings → Environment)
2. Check `.env` file for local development
3. Redeploy after adding missing variables

---

## Testing

### Local Testing
```bash
cd /home/shahar42/Git_Surf_Lamp_Agent/web_and_database
source .env
python3 -c "
from flask import Flask
from flask_mail import Mail, Message
import os

app = Flask(__name__)
app.config.update(
    MAIL_SERVER=os.environ.get('MAIL_SERVER'),
    MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER')
)

mail = Mail(app)

with app.app_context():
    msg = Message('Test', recipients=['your-email@gmail.com'])
    msg.body = 'Test email from Surf Lamp'
    mail.send(msg)
    print('Email sent!')
"
```

### Production Debugging
1. **Check Render logs:**
   ```bash
   # Using MCP tools
   mcp__render__search_render_logs(search_term="mail", limit=100)
   ```

2. **Check Brevo dashboard:**
   - Login: https://app.brevo.com
   - Navigate: Campaigns → Email → Transactional
   - Look for delivery status and error messages

3. **Verify environment variables:**
   ```bash
   mcp__render__render_environment_vars(service_id="srv-d3bddhogjchc73feqi8g")
   ```

---

## Database Queries

### Check Recent Reset Requests
```sql
SELECT
    prt.id,
    u.username,
    u.email,
    prt.created_at,
    prt.expiration_time,
    prt.used_at,
    prt.is_invalidated,
    CASE
        WHEN prt.used_at IS NOT NULL THEN 'USED'
        WHEN prt.is_invalidated THEN 'INVALIDATED'
        WHEN prt.expiration_time < NOW() THEN 'EXPIRED'
        ELSE 'VALID'
    END as token_status
FROM password_reset_tokens prt
JOIN users u ON u.user_id = prt.user_id
ORDER BY prt.created_at DESC
LIMIT 20;
```

### Clean Up Old Tokens (Maintenance)
```sql
DELETE FROM password_reset_tokens
WHERE expiration_time < NOW() - INTERVAL '7 days';
```

---

## File References

### Implementation Files
- **Main App:** `/home/shahar42/Git_Surf_Lamp_Agent/web_and_database/app.py`
  - Lines 152-159: Email configuration
  - Lines 164-191: `send_reset_email()` function
  - Lines 274-316: `/forgot-password` route
  - Lines 318-352: `/reset-password/<token>` route

- **Database Models:** `/home/shahar42/Git_Surf_Lamp_Agent/web_and_database/data_base.py`
  - `PasswordResetToken` model definition

- **Forms:** `/home/shahar42/Git_Surf_Lamp_Agent/web_and_database/forms.py`
  - `ForgotPasswordForm`
  - `ResetPasswordForm`

### Templates
- **Request Form:** `/home/shahar42/Git_Surf_Lamp_Agent/web_and_database/templates/forgot_password.html`
- **Reset Form:** `/home/shahar42/Git_Surf_Lamp_Agent/web_and_database/templates/reset_password.html`

---

## Deployment Checklist

- [ ] All `MAIL_*` environment variables set in Render
- [ ] `MAIL_DEFAULT_SENDER` verified in Brevo dashboard
- [ ] `.python-version` file with Python 3.11.4
- [ ] Database connection using Supabase pooler (IPv4)
- [ ] Flask-Mail in `requirements.txt`
- [ ] `password_reset_tokens` table exists in database
- [ ] HTTPS enabled for production (token in URL)
- [ ] Rate limiting configured (Flask-Limiter + Redis)

---

## Performance Considerations

### Email Sending
- **Synchronous:** Email sent during HTTP request (blocks response)
- **Typical time:** 1-3 seconds for SMTP handoff
- **User experience:** Shows success message immediately after email queued

### Potential Improvements
- **Async email sending:** Use Celery/background worker to avoid blocking HTTP response
- **Email templates:** Use HTML templates with Flask-Mail for better formatting
- **Retry logic:** Implement exponential backoff for failed sends
- **Monitoring:** Set up alerts for high email failure rates

---

## Monitoring & Alerts

### Key Metrics to Track
1. **Password reset request rate** (should be low, spikes indicate issues)
2. **Email delivery success rate** (monitor Brevo dashboard)
3. **Token expiration rate** (users not completing resets)
4. **Failed login attempts after reset** (password complexity issues)

### Brevo Dashboard Metrics
- **Location:** https://app.brevo.com → Campaigns → Email → Transactional
- **Track:** Sent, Delivered, Error, Bounce rates
- **Alert on:** Error rate >10%, Hard bounce rate >5%

---

## Security Audit Checklist

- [x] Tokens cryptographically secure (`secrets.token_urlsafe`)
- [x] Tokens hashed in database (SHA256)
- [x] Tokens expire (20 minutes)
- [x] Tokens single-use (marked `used_at`)
- [x] Old tokens invalidated on new request
- [x] Rate limiting prevents abuse
- [x] No email enumeration (same message for all)
- [x] HTTPS enforced (token in URL encrypted)
- [x] Passwords hashed with bcrypt
- [x] Email validated before sending
- [ ] TODO: Consider adding CAPTCHA for additional abuse prevention
- [ ] TODO: Log all password reset events for security audit trail

---

*Last Updated: 2025-10-01*
*Status: Production - Fully Operational*
