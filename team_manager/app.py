from flask import Flask, render_template, g, request, redirect, url_for
import psycopg2
import psycopg2.extras
import os
import repository

app = Flask(__name__)

def get_db():
    if 'db' not in g:
        db_url = os.environ.get('DATABASE_URL')
        print(f"DEBUG: DATABASE_URL type: {type(db_url)}")
        
        if db_url:
            print(f"DEBUG: DATABASE_URL starts with: {db_url[:15]}...")
            # Auto-append SSL mode for Render
            if 'sslmode' not in db_url:
                 if '?' in db_url:
                    db_url += "&sslmode=require"
                 else:
                    db_url += "?sslmode=require"
        else:
            print("DEBUG: DATABASE_URL is MISSING or Empty!")
            
        g.db = psycopg2.connect(
            db_url,
            cursor_factory=psycopg2.extras.DictCursor
        )
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.route('/')
def dashboard():
    conn = get_db()
    workers = repository.get_all_workers(conn)
    total_workers = len(workers)
    return render_template('dashboard.html', workers=workers, total_workers=total_workers)

@app.route('/worker/<int:worker_id>')
def worker_detail(worker_id):
    conn = get_db()
    worker = repository.get_worker_by_id(conn, worker_id)
    contracts = repository.get_contracts_by_worker_id(conn, worker_id)
    return render_template('worker_detail.html', worker=worker, contracts=contracts)

@app.route('/add_worker', methods=('GET', 'POST'))
def add_worker():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        tags = request.form['tags']
        
        conn = get_db()
        repository.create_worker(conn, name, role, tags)
        return redirect(url_for('dashboard'))
    
    return render_template('add_worker.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
