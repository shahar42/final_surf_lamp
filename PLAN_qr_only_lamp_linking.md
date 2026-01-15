# Plan: QR-Only Lamp Linking

## Problem Statement

The current "Link New Lamp" feature allows users to manually enter any Arduino ID, creating a security vulnerability:
- Users can claim Arduino IDs that haven't been manufactured yet
- When real customers scan QR codes for those IDs, registration fails ("already registered")
- No validation that the Arduino ID physically exists or belongs to the user

## Solution: Smart QR Code Flow

Use the **same QR code** for both registration AND linking additional lamps. The system determines action based on authentication state.

### QR Code URL Format
```
https://surflamp.onrender.com/register?id=12345
```

### Smart Routing Logic

**Scenario 1: User NOT logged in (First-time customer)**
- Scan QR → `/register?id=12345`
- Shows registration form with Arduino ID pre-filled
- Creates new account + links lamp
- **Current behavior - no change**

**Scenario 2: User IS logged in (Existing customer)**
- Scan QR → `/register?id=12345`
- Detect session exists → redirect to `/dashboard/claim-lamp?id=12345`
- New endpoint validates and links lamp
- Show success message → redirect to dashboard

### Benefits
1. **Security**: No manual ID entry = no ID guessing/stealing
2. **Simplicity**: One QR code type for all use cases
3. **User-friendly**: "Just scan the QR code" for any scenario
4. **Manufacturing**: No changes to QR code generation needed

---

## Implementation Steps

### 1. Modify Registration Route (`web_and_database/blueprints/auth.py`)

**Change:** Add authentication check at the top of `/register` route

```python
@bp.route("/register", methods=['GET', 'POST'])
@limiter.limit("10/minute")
def register():
    """
    Handles user registration OR lamp linking (smart routing).
    """
    # NEW: If user already logged in, redirect to claim flow
    if 'user_email' in session:
        arduino_id = request.args.get('id')
        if arduino_id:
            logger.info(f"Logged-in user scanning QR code. Redirecting to claim lamp: {arduino_id}")
            return redirect(url_for('dashboard.claim_lamp', id=arduino_id))
        else:
            # No ID in QR code, just go to dashboard
            return redirect(url_for('dashboard.dashboard'))

    # Existing registration logic (unchanged)...
```

### 2. Create New Endpoint (`web_and_database/blueprints/dashboard.py`)

**Add:** New `/dashboard/claim-lamp` route for logged-in users

```python
@bp.route("/claim-lamp", methods=['GET'])
@login_required
def claim_lamp():
    """
    Claim/link a lamp via QR code scan (for logged-in users).
    """
    user_id = session.get('user_id')
    arduino_id_param = request.args.get('id')

    if not arduino_id_param:
        flash('Invalid QR code. No Arduino ID provided.', 'error')
        return redirect(url_for('dashboard.dashboard'))

    try:
        arduino_id = int(arduino_id_param)
        if not (1 <= arduino_id <= 999999):
            flash('Invalid Arduino ID in QR code.', 'error')
            return redirect(url_for('dashboard.dashboard'))
    except (ValueError, TypeError):
        flash('Invalid QR code format.', 'error')
        return redirect(url_for('dashboard.dashboard'))

    # Get user's current location as default
    from data_base import SessionLocal, User
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        user_location = user.location if user else 'Hadera, Israel'
    finally:
        db.close()

    # Link the Arduino to user
    success, message = add_arduino_to_user(user_id, arduino_id, user_location)

    if success:
        flash(f'Lamp {arduino_id} linked successfully!', 'success')
        logger.info(f"✅ Lamp {arduino_id} linked to user {user_id} via QR code")
    else:
        flash(message, 'error')
        logger.warning(f"❌ Failed to link lamp {arduino_id} to user {user_id}: {message}")

    return redirect(url_for('dashboard.dashboard'))
```

### 3. Update Dashboard UI

**Remove manual form, add QR instruction**

**File:** `web_and_database/templates/dashboard.html`

**Desktop version (lines ~358-394):**
```html
<!-- OLD: Manual form with input fields -->
<button id="showAddArduinoBtn">+ Link New Lamp</button>
<div id="addArduinoForm" class="hidden">
    <input id="newArduinoId" type="number">
    <select id="newArduinoLocation">...</select>
    <button id="submitAddArduino">Link Lamp</button>
</div>

<!-- NEW: Simple instruction -->
<div class="text-center py-3 border-t border-white/20">
    <p class="text-white/80 text-sm mb-2">To link a new lamp:</p>
    <div class="bg-blue-500/20 border border-blue-400 rounded-lg px-4 py-3">
        <p class="text-white font-semibold">📱 Scan the QR code</p>
        <p class="text-white/70 text-xs mt-1">from the card in your lamp box</p>
    </div>
</div>
```

**Mobile version (lines ~240-275):** Same change

### 4. Remove JavaScript Module

**File:** `web_and_database/static/js/features/arduino-management.js`

**Action:** Delete entire file (no longer needed)

**File:** `web_and_database/templates/dashboard.html` (line ~1008)

**Remove:**
```javascript
// Arduino Management (Link New Lamp)
ArduinoManagement.init();
```

### 5. Remove Backend Endpoint

**File:** `web_and_database/blueprints/dashboard.py` (lines 13-36)

**Action:** Delete `/add-arduino` POST endpoint (replaced by `/claim-lamp` GET)

---

## Testing Checklist

### Scenario 1: First-time User
1. Generate QR code for Arduino ID 12345
2. Scan QR → Should land on `/register?id=12345`
3. Fill registration form → Submit
4. Should create account + link lamp → Redirect to dashboard
5. ✅ Arduino 12345 appears in "My Lamps"

### Scenario 2: Existing User - Second Lamp
1. Log in to existing account
2. Scan QR code for Arduino ID 67890 (not yet linked)
3. Should redirect: `/register?id=67890` → `/dashboard/claim-lamp?id=67890`
4. Flash message: "Lamp 67890 linked successfully!"
5. ✅ Arduino 67890 appears in "My Lamps"

### Scenario 3: Already Owned Lamp
1. Log in as User A
2. Scan QR for Arduino ID 12345 (already linked to User A)
3. Should show error: "This Arduino ID is already registered to another user"
4. ✅ No duplicate entry created

### Scenario 4: Stolen QR Code
1. Log in as User A
2. Scan QR for Arduino ID 99999 (linked to User B)
3. Should show error: "This Arduino ID is already registered to another user"
4. ✅ Cannot steal another user's lamp

### Scenario 5: Invalid QR Code
1. Log in to account
2. Manually visit `/register?id=abc` (non-numeric)
3. Should redirect to dashboard with error: "Invalid QR code format"
4. ✅ No crash, graceful error handling

---

## Migration Notes

### Database Changes
- **None required** - uses existing `arduinos` table structure

### Existing Users
- Current manual links remain valid
- Users with multiple lamps unaffected
- No data migration needed

### QR Code Generation
- **No changes needed** - existing QR codes already use `/register?id=X` format
- Tool: `tools/qr_generation/` scripts work as-is

---

## Security Improvements

### Before (Manual Entry)
- User enters Arduino ID 99999 (not manufactured)
- System accepts it if not already claimed
- Real customer can't register later

### After (QR-Only)
- User must have physical QR code from lamp box
- Cannot guess/steal IDs without physical access
- QR codes only generated for manufactured lamps

---

## User Experience

### Old Flow (Multiple Steps)
1. Log in to dashboard
2. Click "+ Link New Lamp"
3. Find Arduino ID on lamp
4. Manually type 6-digit number
5. Select location from dropdown
6. Click "Link Lamp"

### New Flow (Single Scan)
1. Log in to dashboard (or not, if first lamp)
2. Scan QR code → Done

**Reduction: 6 steps → 1 step**

---

## Edge Cases Handled

1. **QR scan without login** → Registration flow (existing behavior)
2. **QR scan while logged in** → Link to existing account (new)
3. **Already owned ID** → Error message, no duplicate
4. **Invalid ID format** → Error message, redirect to dashboard
5. **No ID in URL** → Redirect to dashboard
6. **Arduino already claimed by other user** → Error message (IntegrityError)

---

## Files to Modify

1. ✏️ `web_and_database/blueprints/auth.py` - Add smart routing
2. ✏️ `web_and_database/blueprints/dashboard.py` - Add `/claim-lamp`, remove `/add-arduino`
3. ✏️ `web_and_database/templates/dashboard.html` - Replace form with QR instruction
4. 🗑️ `web_and_database/static/js/features/arduino-management.js` - Delete file

---

## Rollback Plan

If issues arise, rollback commit restores:
- Manual "Link New Lamp" form
- `/add-arduino` POST endpoint
- `arduino-management.js` module

No database changes, so rollback is safe.
