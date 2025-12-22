def get_all_workers(conn):
    """Fetch all workers from the database."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM tm_workers ORDER BY id DESC")
    workers = cur.fetchall()
    cur.close()
    return workers

def get_worker_by_id(conn, worker_id):
    """Fetch a single worker by their ID."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM tm_workers WHERE id = %s", (worker_id,))
    worker = cur.fetchone()
    cur.close()
    return worker

def get_contracts_by_worker_id(conn, worker_id):
    """Fetch all contracts associated with a specific worker."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM tm_contracts WHERE worker_id = %s", (worker_id,))
    contracts = cur.fetchall()
    cur.close()
    return contracts

def create_worker(conn, name, role, tags, image_url=None):
    """Insert a new worker into the database."""
    cur = conn.cursor()
    cur.execute('INSERT INTO tm_workers (name, role, tags, image_url) VALUES (%s, %s, %s, %s)',
               (name, role, tags, image_url))
    conn.commit()
    cur.close()

def update_worker(conn, worker_id, name, role, tags, email, phone, bio, rating, image_url=None):
    """Update an existing worker."""
    cur = conn.cursor()
    cur.execute('''UPDATE tm_workers
                   SET name=%s, role=%s, tags=%s, email=%s, phone=%s, bio=%s, rating=%s, image_url=%s
                   WHERE id=%s''',
               (name, role, tags, email, phone, bio, rating, image_url, worker_id))
    conn.commit()
    cur.close()

def delete_worker(conn, worker_id):
    """Delete a worker and all associated contracts."""
    cur = conn.cursor()
    cur.execute('DELETE FROM tm_workers WHERE id=%s', (worker_id,))
    conn.commit()
    cur.close()

def get_contract_by_id(conn, contract_id):
    """Fetch a single contract by ID."""
    cur = conn.cursor()
    cur.execute('SELECT * FROM tm_contracts WHERE id=%s', (contract_id,))
    contract = cur.fetchone()
    cur.close()
    return contract

def create_contract(conn, worker_id, title, rate, start_date, end_date, terms, status, pdf_filename):
    """Create a new contract."""
    cur = conn.cursor()
    cur.execute('''INSERT INTO tm_contracts
                   (worker_id, title, rate, start_date, end_date, terms, status, pdf_filename)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
               (worker_id, title, rate, start_date, end_date, terms, status, pdf_filename))
    conn.commit()
    cur.close()

def update_contract(conn, contract_id, title, rate, start_date, end_date, terms, status, pdf_filename):
    """Update an existing contract."""
    cur = conn.cursor()
    cur.execute('''UPDATE tm_contracts
                   SET title=%s, rate=%s, start_date=%s, end_date=%s, terms=%s, status=%s, pdf_filename=%s
                   WHERE id=%s''',
               (title, rate, start_date, end_date, terms, status, pdf_filename, contract_id))
    conn.commit()
    cur.close()

def delete_contract(conn, contract_id):
    """Delete a contract."""
    cur = conn.cursor()
    cur.execute('DELETE FROM tm_contracts WHERE id=%s', (contract_id,))
    conn.commit()
    cur.close()

def get_all_contracts(conn):
    """Fetch all contracts with worker names."""
    cur = conn.cursor()
    cur.execute('''SELECT c.*, w.name as worker_name
                   FROM tm_contracts c
                   LEFT JOIN tm_workers w ON c.worker_id = w.id
                   ORDER BY c.start_date DESC''')
    contracts = cur.fetchall()
    cur.close()
    return contracts

def search_workers(conn, query):
    """Search workers by name, role, or tags."""
    cur = conn.cursor()
    search_term = f'%{query}%'
    cur.execute('''SELECT * FROM tm_workers
                   WHERE name ILIKE %s OR role ILIKE %s OR tags ILIKE %s
                   ORDER BY id DESC''',
               (search_term, search_term, search_term))
    workers = cur.fetchall()
    cur.close()
    return workers
