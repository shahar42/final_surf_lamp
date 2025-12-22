DROP TABLE IF EXISTS workers;
DROP TABLE IF EXISTS contracts;

CREATE TABLE workers (
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

CREATE TABLE contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    rate TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    terms TEXT,
    status TEXT DEFAULT 'Active',
    FOREIGN KEY (worker_id) REFERENCES workers (id)
);
