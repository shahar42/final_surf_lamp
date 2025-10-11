#!/usr/bin/env python3
"""
Password Reset Token Cleanup Script

Deletes expired, used, or invalidated password reset tokens from the database.

This script should be run periodically (e.g., daily via cron) to prevent
unbounded table growth.

Usage:
    python3 cleanup_tokens.py

Cron example (run daily at 3 AM):
    0 3 * * * cd /path/to/project && python3 cleanup_tokens.py >> /var/log/token_cleanup.log 2>&1
"""

import os
import sys

# Add parent directory to path so we can import from web_and_database
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'web_and_database'))

from data_base import cleanup_expired_password_reset_tokens

if __name__ == '__main__':
    print("🧹 Starting password reset token cleanup...")

    deleted_count = cleanup_expired_password_reset_tokens()

    if deleted_count > 0:
        print(f"✅ Successfully deleted {deleted_count} expired tokens")
    else:
        print("ℹ️  No tokens to clean up")

    sys.exit(0)
