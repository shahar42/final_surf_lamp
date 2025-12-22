DROP TABLE IF EXISTS tm_contracts;
DROP TABLE IF EXISTS tm_workers;

CREATE TABLE tm_workers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    tags TEXT,
    rating INTEGER DEFAULT 5,
    email TEXT,
    phone TEXT,
    bio TEXT,
    image_url TEXT
);

CREATE TABLE tm_contracts (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    rate TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    terms TEXT,
    status TEXT DEFAULT 'Active',
    pdf_filename TEXT,
    CONSTRAINT fk_worker
        FOREIGN KEY (worker_id)
        REFERENCES tm_workers (id)
        ON DELETE CASCADE
);