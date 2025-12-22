import os
import psycopg2
from urllib.parse import urlparse
import database
from config import config

def init_db():
    env_name = os.environ.get('FLASK_ENV', 'default')
    database_url = config[env_name].DATABASE_URL
    
    print("--- Database Initialization ---")
    if not database_url:
        print("WARNING: DATABASE_URL environment variable is NOT set.")
        print("Skipping database initialization.")
        return

    # Mask password for logging
    safe_url = database_url
    if '@' in safe_url:
        part1, part2 = safe_url.split('@')
        safe_url = f"{part1.split(':')[0]}:****@{part2}"
    print(f"Target Database: {safe_url}")

    # Parse URL to check for host
    result = urlparse(database_url)
    if not result.hostname:
        print("ERROR: DATABASE_URL does not contain a hostname!")
        print("Please ensure it follows the format: postgres://user:pass@host:port/dbname")
        # Exit with error to fail build if URL is clearly bad
        exit(1)

    try:
        # database.get_connection handles SSL mode
        conn = database.get_connection(database_url)
        cur = conn.cursor()
        
        print("Connected successfully. Applying schema...")
        with open('schema.sql') as f:
            # Execute schema script
            cur.execute(f.read())
        
        conn.commit()
        cur.close()
        conn.close()
        print("SUCCESS: Database initialized (Postgres).")
        
    except psycopg2.OperationalError as e:
        print(f"CONNECTION ERROR: {e}")
        print("Check your DATABASE_URL, IP Allowlist (0.0.0.0/0), and Region.")
        # Fail the build so we know it didn't work
        exit(1)
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        exit(1)

if __name__ == '__main__':
    init_db()