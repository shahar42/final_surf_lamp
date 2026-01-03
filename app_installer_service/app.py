from flask import Flask, render_template, send_file, abort
import os

app = Flask(__name__)

# Configuration
INSTALLER_FILENAME = "kerados_installer.exe"
DOWNLOADS_DIR = os.path.join(app.root_path, 'static', 'downloads')

@app.route('/')
def index():
    """Landing page with download button"""
    return render_template('index.html')

@app.route('/download')
def download_installer():
    """Serve the Kerados installer"""
    file_path = os.path.join(DOWNLOADS_DIR, INSTALLER_FILENAME)

    if not os.path.exists(file_path):
        abort(404, description="Installer file not found")

    return send_file(
        file_path,
        as_attachment=True,
        download_name=INSTALLER_FILENAME,
        mimetype='application/octet-stream'
    )

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return {"status": "healthy"}, 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
