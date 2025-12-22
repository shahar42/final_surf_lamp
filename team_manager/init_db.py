import sqlite3

def init_db():
    connection = sqlite3.connect('staff_command.db')
    with open('schema.sql') as f:
        connection.executescript(f.read())
    
    cur = connection.cursor()
    
    # Seed Workers
    cur.execute("INSERT INTO workers (name, role, tags, rating, email, bio) VALUES (?, ?, ?, ?, ?, ?)",
                ('Alex "Knuckles" McGinty', 'Logistics Lead', 'Heavy Lift,Night Shift,Certified', 5, 'alex@example.com', 'Reliable but needs coffee before 8am. 10 years experience.'))
    
    cur.execute("INSERT INTO workers (name, role, tags, rating, email, bio) VALUES (?, ?, ?, ?, ?, ?)",
                ('Sarah Vance', 'Event Coordinator', 'VIP Handling,Fluent French', 4, 'sarah@example.com', 'Great with clients. Prefer weekend shifts.'))
    
    cur.execute("INSERT INTO workers (name, role, tags, rating, email, bio) VALUES (?, ?, ?, ?, ?, ?)",
                ('Davide Rossi', 'Site Safety', 'First Aid,OSHA 30', 5, 'davide@example.com', 'Strict on protocols. Do not double book.'))

    # Seed Contracts
    cur.execute("INSERT INTO contracts (worker_id, title, rate, start_date, terms, status) VALUES (?, ?, ?, ?, ?, ?)",
                (1, '2024 Season Agreement', '$32.50/hr', '2024-05-01', 'Standard liability waiver included.', 'Active'))
    
    cur.execute("INSERT INTO contracts (worker_id, title, rate, start_date, terms, status) VALUES (?, ?, ?, ?, ?, ?)",
                (2, 'Fall Gala Retainer', '$4000 Flat', '2024-09-01', 'Includes travel expenses.', 'Draft'))

    connection.commit()
    connection.close()
    print("Database initialized and seeded.")

if __name__ == '__main__':
    init_db()
