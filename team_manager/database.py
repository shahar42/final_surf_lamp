import psycopg2
import psycopg2.extras

def get_connection(db_url):
    """
    Creates and returns a new database connection.
    Handles Render-specific SSL requirements.
    """
    if not db_url:
        # In a real app, use logging instead of print
        print("DEBUG: DATABASE_URL is MISSING or Empty!")
        raise ValueError("DATABASE_URL is not set")

    # Auto-append SSL mode for Render
    if 'sslmode' not in db_url:
        if '?' in db_url:
            db_url += "&sslmode=require"
        else:
            db_url += "?sslmode=require"

    return psycopg2.connect(
        db_url,
        cursor_factory=psycopg2.extras.DictCursor
    )
