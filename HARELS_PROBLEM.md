# Harel's Login Problem

## Issue
User Harel successfully registered but could not login, receiving "Invalid email or password" error despite using correct credentials.

## Root Cause
Registration form validated email in lowercase but didn't modify `field.data`, causing mixed-case emails (e.g., `Harel@Gmail.com`) to be stored in database. Login form used case-sensitive SQL query (`User.email == email`), so `harel@gmail.com` didn't match `Harel@Gmail.com` in database.

## Solution Implemented
Changed login query to case-insensitive comparison using `func.lower(User.email) == email.lower()` in `app.py:578`. Registration form now only strips whitespace, preserving original email capitalization as user typed it. Added comprehensive login logging to track attempts, showing exact email used and failure reason (email not found vs wrong password).

## Testing
Created test user with `TestUser@Gmail.Com` (mixed case) and confirmed login works with `testuser@gmail.com` (lowercase). User deleted from database, will re-register tomorrow to verify fix in production.

## Files Changed
- `web_and_database/app.py` - Case-insensitive login query + detailed logging
- `web_and_database/forms.py` - Registration preserves email case, login strips whitespace only

## Commits
- `2cf63f8` - Fix email case sensitivity correctly
- `1b01679` - Add comprehensive login logging for debugging
