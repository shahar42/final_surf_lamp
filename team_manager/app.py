from flask import Flask, render_template, g, request, redirect, url_for
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__)

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(
            os.environ.get('DATABASE_URL'),
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
    cur = conn.cursor()
    cur.execute("SELECT * FROM tm_workers")
    workers = cur.fetchall()
    cur.close()
    
    total_workers = len(workers)
    return render_template('dashboard.html', workers=workers, total_workers=total_workers)

@app.route('/worker/<int:worker_id>')
def worker_detail(worker_id):
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM tm_workers WHERE id = %s", (worker_id,))
    worker = cur.fetchone()
    
    cur.execute("SELECT * FROM tm_contracts WHERE worker_id = %s", (worker_id,))
    contracts = cur.fetchall()
    cur.close()
    
    return render_template('worker_detail.html', worker=worker, contracts=contracts)

@app.route('/add_worker', methods=('GET', 'POST'))
def add_worker():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        tags = request.form['tags']
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute('INSERT INTO tm_workers (name, role, tags) VALUES (%s, %s, %s)',
                   (name, role, tags))
        conn.commit()
        cur.close()
        return redirect(url_for('dashboard'))
    
    return render_template('add_worker.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)