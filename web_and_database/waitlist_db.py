"""
Waitlist Database Management
Stores waitlist signups in Google Sheets (persistent across Render restarts).
"""
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

SHEET_ID = '1YOD0rNt_FXNTXNYMBHEUsR6QrKhA5QYe5WxPkyMEeSw'
SHEET_NAME = 'Waitlist'

# Column order in the sheet
HEADERS = ['id', 'first_name', 'last_name', 'email', 'phone', 'signup_date', 'ip_address', 'user_agent', 'notified']


def _get_sheet():
    """Authenticate and return the worksheet."""
    import gspread

    # Try env var first (production), fall back to local file (dev)
    creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    if creds_json:
        creds_dict = json.loads(creds_json)
        client = gspread.service_account_from_dict(creds_dict)
    else:
        creds_file = os.path.join(os.path.dirname(__file__), '..', 'landing_page', 'meta-notch-447113-c0-87a12306fd18.json')
        client = gspread.service_account(filename=creds_file)
    spreadsheet = client.open_by_key(SHEET_ID)

    # Get or create the worksheet
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=len(HEADERS))
        worksheet.append_row(HEADERS)

    return worksheet


def add_to_waitlist(first_name, last_name, email, phone=None, ip_address=None, user_agent=None):
    """
    Add a new entry to the waitlist.

    Returns:
        tuple: (success: bool, message: str, waitlist_position: int or None)
    """
    try:
        sheet = _get_sheet()
        email_lower = email.lower()

        # Check for duplicate email
        all_values = sheet.get_all_values()
        for row in all_values[1:]:  # skip header
            if len(row) >= 4 and row[3].lower() == email_lower:
                return False, "This email is already on the waitlist", None

        # Generate next id
        data_rows = all_values[1:] if len(all_values) > 1 else []
        next_id = len(data_rows) + 1

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
        sheet.append_row(new_row, value_input_option='RAW')

        position = next_id
        return True, "Successfully added to waitlist", position

    except Exception as e:
        logger.error(f"Google Sheets waitlist error: {e}")
        return False, f"Error: {str(e)}", None


def get_waitlist_count():
    """Get total number of waitlist signups."""
    try:
        sheet = _get_sheet()
        all_values = sheet.get_all_values()
        return max(0, len(all_values) - 1)  # subtract header row
    except Exception as e:
        logger.error(f"Google Sheets count error: {e}")
        return 0


def get_all_waitlist_entries():
    """
    Get all waitlist entries for admin dashboard.

    Returns:
        list: List of dictionaries with waitlist data
    """
    try:
        sheet = _get_sheet()
        all_values = sheet.get_all_values()
        if len(all_values) <= 1:
            return []
        headers = all_values[0]
        return [dict(zip(headers, row)) for row in reversed(all_values[1:])]
    except Exception as e:
        logger.error(f"Google Sheets get_all error: {e}")
        return []


def mark_as_notified(email):
    """Mark a waitlist entry as notified."""
    try:
        sheet = _get_sheet()
        cell = sheet.find(email.lower(), in_column=4)  # email is column 4
        if cell:
            notified_col = HEADERS.index('notified') + 1
            sheet.update_cell(cell.row, notified_col, 'true')
    except Exception as e:
        logger.error(f"Google Sheets mark_notified error: {e}")


def get_recent_signups(hours=24):
    """Get signups from the last N hours."""
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
