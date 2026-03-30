import sqlite3

def dict_factory(cursor, row):
    """Convert SQLite rows to dictionaries (like psycopg2.extras.DictCursor)"""
    fields = [column[0] for column in cursor.description]
    return dict(zip(fields, row))

def get_connection(db_path):
    """
    Creates and returns a new SQLite database connection.
    """
    if not db_path:
        db_path = 'staff_command.db'  # Default SQLite database

    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory  # Return rows as dictionaries
    return conn
