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

def create_worker(conn, name, role, tags):
    """Insert a new worker into the database."""
    cur = conn.cursor()
    cur.execute('INSERT INTO tm_workers (name, role, tags) VALUES (%s, %s, %s)',
               (name, role, tags))
    conn.commit()
    cur.close()
