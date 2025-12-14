"""
Waitlist Database Management
Simple SQLite database for managing product waitlist signups.
"""
import sqlite3
import os
from datetime import datetime
from pathlib import Path

# Database file path - stored in web_and_database directory
DB_PATH = Path(__file__).parent / 'waitlist.db'


def init_waitlist_db():
    """Initialize the waitlist database with required schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            signup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            notified BOOLEAN DEFAULT 0
        )
    ''')

    # Index for faster email lookups (prevent duplicates)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_email ON waitlist(email)
    ''')

    # Index for signup date (admin dashboard sorting)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_signup_date ON waitlist(signup_date DESC)
    ''')

    conn.commit()
    conn.close()


def add_to_waitlist(first_name, last_name, email, phone=None, ip_address=None, user_agent=None):
    """
    Add a new entry to the waitlist.

    Returns:
        tuple: (success: bool, message: str, waitlist_position: int or None)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO waitlist (first_name, last_name, email, phone, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (first_name, last_name, email.lower(), phone, ip_address, user_agent))

        conn.commit()

        # Get waitlist position (total count)
        cursor.execute('SELECT COUNT(*) FROM waitlist')
        position = cursor.fetchone()[0]

        return True, "Successfully added to waitlist", position

    except sqlite3.IntegrityError:
        return False, "This email is already on the waitlist", None
    except Exception as e:
        return False, f"Database error: {str(e)}", None
    finally:
        conn.close()


def get_waitlist_count():
    """Get total number of waitlist signups."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM waitlist')
    count = cursor.fetchone()[0]

    conn.close()
    return count


def get_all_waitlist_entries():
    """
    Get all waitlist entries for admin dashboard.

    Returns:
        list: List of dictionaries with waitlist data
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, first_name, last_name, email, phone, signup_date, notified
        FROM waitlist
        ORDER BY signup_date DESC
    ''')

    entries = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return entries


def mark_as_notified(email):
    """Mark a waitlist entry as notified."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('UPDATE waitlist SET notified = 1 WHERE email = ?', (email.lower(),))
    conn.commit()
    conn.close()


def get_recent_signups(hours=24):
    """Get signups from the last N hours."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT first_name, last_name, email, signup_date
        FROM waitlist
        WHERE datetime(signup_date) > datetime('now', '-' || ? || ' hours')
        ORDER BY signup_date DESC
    ''', (hours,))

    entries = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return entries


# Initialize database on module import
if not DB_PATH.exists():
    init_waitlist_db()
