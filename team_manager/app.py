from flask import Flask, render_template, g, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
import repository
import database
from config import config
from storage import LocalStorageService

app = Flask(__name__)
env_name = os.environ.get('FLASK_ENV', 'default')
app.config.from_object(config[env_name])

storage_service = LocalStorageService(app.config)

def get_db():
    if 'db' not in g:
        g.db = database.get_connection(app.config['DATABASE_URL'])
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.route('/')
def dashboard():
    conn = get_db()
    query = request.args.get('q', '')
    if query:
        workers = repository.search_workers(conn, query)
    else:
        workers = repository.get_all_workers(conn)
    total_workers = len(workers)
    search_enabled = app.config['ENABLE_SEARCH']
    return render_template('dashboard.html', workers=workers, total_workers=total_workers, search_query=query, search_enabled=search_enabled)

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
        tags = request.form.get('tags', '')

        image_url = None
        if 'profile_image' in request.files:
             saved_path = storage_service.save_profile(request.files['profile_image'])
             if saved_path:
                 image_url = saved_path

        conn = get_db()
        repository.create_worker(conn, name, role, tags, image_url)
        return redirect(url_for('dashboard'))

    return render_template('add_worker.html')

@app.route('/worker/<int:worker_id>/edit', methods=('GET', 'POST'))
def edit_worker(worker_id):
    conn = get_db()
    worker = repository.get_worker_by_id(conn, worker_id)

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        tags = request.form.get('tags', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        bio = request.form.get('bio', '')
        rating = request.form.get('rating', 5)

        image_url = worker.image_url
        if 'profile_image' in request.files:
            saved_path = storage_service.save_profile(request.files['profile_image'])
            if saved_path:
                image_url = saved_path

        repository.update_worker(conn, worker_id, name, role, tags, email, phone, bio, rating, image_url)
        return redirect(url_for('worker_detail', worker_id=worker_id))

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
        payment_type = request.form.get('payment_type', 'Monthly Salary')
        start_date = request.form['start_date']
        end_date = request.form.get('end_date', '')
        terms = request.form.get('terms', '')
        status = request.form.get('status', 'Active')

        pdf_filename = None
        if 'pdf' in request.files:
            saved_name = storage_service.save_contract(request.files['pdf'])
            if saved_name:
                pdf_filename = saved_name

        repository.create_contract(conn, worker_id, title, rate, payment_type, start_date, end_date, terms, status, pdf_filename)
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
        payment_type = request.form.get('payment_type', 'Monthly Salary')
        start_date = request.form['start_date']
        end_date = request.form.get('end_date', '')
        terms = request.form.get('terms', '')
        status = request.form.get('status', 'Active')

        pdf_filename = contract.pdf_filename
        if 'pdf' in request.files:
            saved_name = storage_service.save_contract(request.files['pdf'])
            if saved_name:
                pdf_filename = saved_name

        repository.update_contract(conn, contract_id, title, rate, payment_type, start_date, end_date, terms, status, pdf_filename)
        return redirect(url_for('worker_detail', worker_id=contract.worker_id))

    return render_template('edit_contract.html', contract=contract)

@app.route('/contract/<int:contract_id>/delete', methods=('POST',))
def delete_contract(contract_id):
    conn = get_db()
    contract = repository.get_contract_by_id(conn, contract_id)
    worker_id = contract.worker_id
    repository.delete_contract(conn, contract_id)
    return redirect(url_for('worker_detail', worker_id=worker_id))

@app.route('/contract/<int:contract_id>/delete_file', methods=('POST',))
def delete_contract_file(contract_id):
    conn = get_db()
    contract = repository.get_contract_by_id(conn, contract_id)

    if contract.pdf_filename:
        storage_service.delete_contract(contract.pdf_filename)

    repository.update_contract(conn, contract_id, contract.title, contract.rate,
                              contract.payment_type, contract.start_date, contract.end_date,
                              contract.terms, contract.status, None)
    return redirect(url_for('worker_detail', worker_id=contract.worker_id))

@app.route('/contracts')
def contracts():
    conn = get_db()
    contracts = repository.get_all_contracts(conn)
    return render_template('contracts.html', contracts=contracts)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
