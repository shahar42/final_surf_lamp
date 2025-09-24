#!/usr/bin/env python3
"""
Database migration script to add the sport_type column to the users table.
This fixes the production error: column users.sport_type does not exist

Run this script to add the missing column with a default value.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def add_sport_type_column():
    """Add sport_type column to users table with default value."""

    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False

    try:
        # Create engine
        engine = create_engine(database_url)

        # Add the column with default value
        with engine.connect() as conn:
            # Add column with default value 'surfing'
            sql = text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS sport_type VARCHAR(20)
                NOT NULL DEFAULT 'surfing'
            """)

            conn.execute(sql)
            conn.commit()

            print("✅ Successfully added sport_type column to users table")

            # Verify the column was added
            verify_sql = text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'sport_type'
            """)

            result = conn.execute(verify_sql)
            row = result.fetchone()

            if row:
                print(f"✅ Column verified: {row.column_name} ({row.data_type}), nullable: {row.is_nullable}, default: {row.column_default}")
                return True
            else:
                print("❌ Column verification failed")
                return False

    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Adding sport_type column to users table...")

    if add_sport_type_column():
        print("🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        print("💥 Migration failed!")
        sys.exit(1)