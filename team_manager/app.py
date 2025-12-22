from flask import Flask, render_template, g, request, redirect, url_for
import sqlite3

app = Flask(__name__)
DATABASE = 'staff_command.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def dashboard():
    cur = get_db().cursor()
    cur.execute("SELECT * FROM workers")
    workers = cur.fetchall()
    
    # Simple count stats
    total_workers = len(workers)
    
    return render_template('dashboard.html', workers=workers, total_workers=total_workers)

@app.route('/worker/<int:worker_id>')
def worker_detail(worker_id):
    cur = get_db().cursor()
    cur.execute("SELECT * FROM workers WHERE id = ?", (worker_id,))
    worker = cur.fetchone()
    
    cur.execute("SELECT * FROM contracts WHERE worker_id = ?", (worker_id,))
    contracts = cur.fetchall()
    
    return render_template('worker_detail.html', worker=worker, contracts=contracts)

@app.route('/add_worker', methods=('GET', 'POST'))
def add_worker():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        tags = request.form['tags']
        
        db = get_db()
        db.execute('INSERT INTO workers (name, role, tags) VALUES (?, ?, ?)',
                   (name, role, tags))
        db.commit()
        return redirect(url_for('dashboard'))
    
    return render_template('add_worker.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
