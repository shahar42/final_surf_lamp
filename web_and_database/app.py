from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from config import configure_app
from utils.helpers import convert_wind_direction
from flask import redirect, url_for
from blueprints import (
    auth, dashboard, api_user,
    api_arduino, api_chat, reports, admin, landing
)

def create_app():
    app = Flask(__name__)

    # Configure app
    configure_app(app)

    # Fix for Render's reverse proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Register filters
    app.jinja_env.filters['wind_direction'] = convert_wind_direction

    # Register blueprints
    app.register_blueprint(landing.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(api_user.bp)
    app.register_blueprint(api_arduino.bp)
    app.register_blueprint(api_chat.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(admin.bp)

    # Root route redirects to dashboard (which auto-redirects to login if not logged in)
    @app.route('/')
    def index():
        return redirect(url_for('dashboard.dashboard'))

    return app

app = create_app()

if __name__ == '__main__':
    import os
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5001, debug=debug_mode)