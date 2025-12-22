import sqlite3

def init_db():
    connection = sqlite3.connect('staff_command.db')
    with open('schema.sql') as f:
        connection.executescript(f.read())
    
    cur = connection.cursor()
    
    # Seed Workers (Removed for production)
    # Workers and Contracts tables will be empty on initialization.

    connection.commit()
    connection.close()
    print("Database initialized (empty).")

if __name__ == '__main__':
    init_db()
