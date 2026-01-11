import os
import sqlite3
import database
from config import config

def init_db():
    env_name = os.environ.get('FLASK_ENV', 'default')
    # For SQLite, DATABASE_URL in config is the file path (e.g., 'staff_command.db')
    db_path = config[env_name].DATABASE_URL
    
    print("--- Database Initialization ---")
    print(f"Target Database File: {db_path}")

    try:
        # Connect using the shared logic (which returns a sqlite3 connection)
        conn = database.get_connection(db_path)
        cur = conn.cursor()
        
        print("Connected successfully. Applying schema...")
        with open('schema.sql') as f:
            # executescript is specifically for running multiple SQL statements (semicolon-separated)
            cur.executescript(f.read())
        
        conn.commit()
        # Close cursor/connection
        cur.close()
        conn.close()
        print("SUCCESS: Database initialized (SQLite).")
        
    except sqlite3.Error as e:
        print(f"SQLITE ERROR: {e}")
        exit(1)
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        exit(1)

if __name__ == '__main__':
    init_db()