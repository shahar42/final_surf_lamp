import os
import psycopg2
from urllib.parse import urlparse

def init_db():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        # Fallback for local testing if env var not set
        print("DATABASE_URL not set. Skipping DB init.")
        return

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    with open('schema.sql') as f:
        conn.cursor().execute(f.read())
        # Note: createscript is sqlite specific, for pg we execute the sql string
        # But split by statement if needed. 
        # Simpler approach for this schema:
        sql_commands = f.read().split(';')
        for command in sql_commands:
            if command.strip():
                cur.execute(command)
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database initialized (Postgres).")

if __name__ == '__main__':
    init_db()