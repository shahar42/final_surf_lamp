from flask import Flask, render_template, g, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import psycopg2
import psycopg2.extras
import os
import repository

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
UPLOAD_FOLDER = 'static/uploads/contracts'
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def dashboard():
    conn = get_db()
    query = request.args.get('q', '')
    if query:
        workers = repository.search_workers(conn, query)
    else:
        workers = repository.get_all_workers(conn)
    total_workers = len(workers)
    return render_template('dashboard.html', workers=workers, total_workers=total_workers, search_query=query)

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

@app.route('/worker/<int:worker_id>/edit', methods=('GET', 'POST'))
def edit_worker(worker_id):
    conn = get_db()
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        tags = request.form.get('tags', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        bio = request.form.get('bio', '')
        rating = request.form.get('rating', 5)

        repository.update_worker(conn, worker_id, name, role, tags, email, phone, bio, rating)
        return redirect(url_for('worker_detail', worker_id=worker_id))

    worker = repository.get_worker_by_id(conn, worker_id)
    return render_template('edit_worker.html', worker=worker)

@app.route('/worker/<int:worker_id>/delete', methods=('POST',))
def delete_worker(worker_id):
    conn = get_db()
    repository.delete_worker(conn, worker_id)
    return redirect(url_for('dashboard'))

@app.route('/worker/<int:worker_id>/add_contract', methods=('GET', 'POST'))
def add_contract(worker_id):
    conn = get_db()
    if request.method == 'POST':
        title = request.form['title']
        rate = request.form['rate']
        start_date = request.form['start_date']
        end_date = request.form.get('end_date', '')
        terms = request.form.get('terms', '')
        status = request.form.get('status', 'Active')

        pdf_filename = None
        if 'pdf' in request.files:
            file = request.files['pdf']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                pdf_filename = filename
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)

        repository.create_contract(conn, worker_id, title, rate, start_date, end_date, terms, status, pdf_filename)
        return redirect(url_for('worker_detail', worker_id=worker_id))

    worker = repository.get_worker_by_id(conn, worker_id)
    return render_template('add_contract.html', worker=worker)

@app.route('/contract/<int:contract_id>/edit', methods=('GET', 'POST'))
def edit_contract(contract_id):
    conn = get_db()
    contract = repository.get_contract_by_id(conn, contract_id)

    if request.method == 'POST':
        title = request.form['title']
        rate = request.form['rate']
        start_date = request.form['start_date']
        end_date = request.form.get('end_date', '')
        terms = request.form.get('terms', '')
        status = request.form.get('status', 'Active')

        pdf_filename = contract['pdf_filename']
        if 'pdf' in request.files:
            file = request.files['pdf']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                pdf_filename = filename
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)

        repository.update_contract(conn, contract_id, title, rate, start_date, end_date, terms, status, pdf_filename)
        return redirect(url_for('worker_detail', worker_id=contract['worker_id']))

    return render_template('edit_contract.html', contract=contract)

@app.route('/contract/<int:contract_id>/delete', methods=('POST',))
def delete_contract(contract_id):
    conn = get_db()
    contract = repository.get_contract_by_id(conn, contract_id)
    worker_id = contract['worker_id']
    repository.delete_contract(conn, contract_id)
    return redirect(url_for('worker_detail', worker_id=worker_id))

@app.route('/contracts')
def contracts():
    conn = get_db()
    contracts = repository.get_all_contracts(conn)
    return render_template('contracts.html', contracts=contracts)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
