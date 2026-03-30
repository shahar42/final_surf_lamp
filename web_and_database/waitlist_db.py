"""
Waitlist Database Management
Stores waitlist signups in Google Sheets via REST API (gevent-compatible).
"""
import os
import json
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

SHEET_ID = '1YOD0rNt_FXNTXNYMBHEUsR6QrKhA5QYe5WxPkyMEeSw'
SHEET_NAME = 'Waitlist'
HEADERS = ['id', 'first_name', 'last_name', 'email', 'phone', 'signup_date', 'ip_address', 'user_agent', 'notified']

SHEETS_API = 'https://sheets.googleapis.com/v4/spreadsheets'
TOKEN_URL = 'https://oauth2.googleapis.com/token'


def _get_access_token(creds_dict):
    """Get a short-lived OAuth2 access token using a service account JWT."""
    import urllib.request
    import urllib.parse
    import base64
    import hashlib
    import hmac
    import struct

    # Build JWT header + claims
    now = int(time.time())
    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).rstrip(b'=')
    claims = base64.urlsafe_b64encode(json.dumps({
        "iss": creds_dict["client_email"],
        "scope": "https://www.googleapis.com/auth/spreadsheets",
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }).encode()).rstrip(b'=')

    # Sign with RSA private key
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    private_key = serialization.load_pem_private_key(
        creds_dict["private_key"].encode(), password=None
    )
    signing_input = header + b'.' + claims
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    jwt = signing_input + b'.' + base64.urlsafe_b64encode(signature).rstrip(b'=')

    # Exchange JWT for access token
    data = urllib.parse.urlencode({
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': jwt.decode(),
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method='POST')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())['access_token']


def _get_creds():
    creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    if creds_json:
        return json.loads(creds_json)
    creds_file = os.path.join(os.path.dirname(__file__), '..', 'landing_page', 'meta-notch-447113-c0-87a12306fd18.json')
    with open(creds_file) as f:
        return json.load(f)


def _api_get(token, path):
    import urllib.request
    req = urllib.request.Request(f'{SHEETS_API}/{SHEET_ID}{path}')
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _api_post(token, path, body):
    import urllib.request
    data = json.dumps(body).encode()
    req = urllib.request.Request(f'{SHEETS_API}/{SHEET_ID}{path}', data=data, method='POST')
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _ensure_sheet_exists(token):
    """Create the Waitlist sheet with headers if it doesn't exist."""
    meta = _api_get(token, '')
    titles = [s['properties']['title'] for s in meta.get('sheets', [])]
    if SHEET_NAME not in titles:
        _api_post(token, ':batchUpdate', {
            'requests': [{'addSheet': {'properties': {'title': SHEET_NAME}}}]
        })
        _api_post(token, f'/values/{SHEET_NAME}!A1:append', {
            'values': [HEADERS]
        })


def _get_all_rows(token):
    try:
        result = _api_get(token, f'/values/{SHEET_NAME}')
        return result.get('values', [])
    except Exception:
        return []


def add_to_waitlist(first_name, last_name, email, phone=None, ip_address=None, user_agent=None):
    try:
        creds = _get_creds()
        token = _get_access_token(creds)
        _ensure_sheet_exists(token)

        rows = _get_all_rows(token)
        email_lower = email.lower()

        # Check duplicate (skip header row)
        for row in rows[1:]:
            if len(row) >= 4 and row[3].lower() == email_lower:
                return False, "This email is already on the waitlist", None

        next_id = len(rows)  # rows includes header, so len = next id
        new_row = [
            next_id,
            first_name,
            last_name,
            email_lower,
            phone or '',
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            ip_address or '',
            user_agent or '',
            'false',
        ]
        _api_post(token, f'/values/{SHEET_NAME}!A1:append?valueInputOption=RAW', {
            'values': [new_row]
        })
        return True, "Successfully added to waitlist", next_id

    except Exception as e:
        logger.error(f"Google Sheets waitlist error: {e}")
        return False, f"Error: {str(e)}", None


def get_waitlist_count():
    try:
        creds = _get_creds()
        token = _get_access_token(creds)
        rows = _get_all_rows(token)
        return max(0, len(rows) - 1)
    except Exception as e:
        logger.error(f"Google Sheets count error: {e}")
        return 0


def get_all_waitlist_entries():
    try:
        creds = _get_creds()
        token = _get_access_token(creds)
        rows = _get_all_rows(token)
        if len(rows) <= 1:
            return []
        headers = rows[0]
        return [dict(zip(headers, row)) for row in reversed(rows[1:])]
    except Exception as e:
        logger.error(f"Google Sheets get_all error: {e}")
        return []


def mark_as_notified(email):
    try:
        creds = _get_creds()
        token = _get_access_token(creds)
        rows = _get_all_rows(token)
        for i, row in enumerate(rows[1:], start=2):
            if len(row) >= 4 and row[3].lower() == email.lower():
                notified_col = HEADERS.index('notified') + 1
                col_letter = chr(ord('A') + notified_col - 1)
                import urllib.request
                data = json.dumps({'values': [['true']]}).encode()
                req = urllib.request.Request(
                    f'{SHEETS_API}/{SHEET_ID}/values/{SHEET_NAME}!{col_letter}{i}?valueInputOption=RAW',
                    data=data, method='PUT'
                )
                req.add_header('Authorization', f'Bearer {token}')
                req.add_header('Content-Type', 'application/json')
                urllib.request.urlopen(req)
                break
    except Exception as e:
        logger.error(f"Google Sheets mark_notified error: {e}")


def get_recent_signups(hours=24):
    try:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        entries = get_all_waitlist_entries()
        recent = []
        for entry in entries:
            try:
                signup_dt = datetime.strptime(entry.get('signup_date', ''), '%Y-%m-%d %H:%M:%S')
                if signup_dt >= cutoff:
                    recent.append(entry)
            except ValueError:
                pass
        return recent
    except Exception as e:
        logger.error(f"Google Sheets recent_signups error: {e}")
        return []
