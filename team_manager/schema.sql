CREATE TABLE IF NOT EXISTS tm_workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    tags TEXT,
    rating INTEGER DEFAULT 5,
    email TEXT,
    phone TEXT,
    bio TEXT,
    image_url TEXT
);

CREATE TABLE IF NOT EXISTS tm_contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    rate TEXT NOT NULL,
    payment_type TEXT DEFAULT 'Monthly Salary',
    start_date TEXT NOT NULL,
    end_date TEXT,
    terms TEXT,
    status TEXT DEFAULT 'Active',
    pdf_filename TEXT,
    FOREIGN KEY (worker_id)
        REFERENCES tm_workers (id)
        ON DELETE CASCADE
);