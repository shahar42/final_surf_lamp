"""
Surf Lamp System Visualization Server
Serves interactive D3.js visualization of system architecture
"""
from flask import Flask, render_template, jsonify, abort
from flask_cors import CORS
import os
from dotenv import load_dotenv
import markdown2

load_dotenv()

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
CORS(app)

# System architecture data
SYSTEM_DATA = {
    "nodes": [
        {"id": "web", "name": "Web Application", "type": "backend", "description": "Flask web server displaying user dashboard. Handles user authentication, configuration and data display.", "size": 1800},
        {"id": "database", "name": "Database (Supabase)", "type": "storage", "description": "database hosted on Supabase storing all system data. location_websites mapping, source of truth for the entire system.", "size": 1500},
        {"id": "redis", "name": "Redis Cache", "type": "storage", "description": "In-memory cache service providing rate limiting for user actions. Prevents API abuse by blocking rapid successive changes.", "size": 500},
        {"id": "processor", "name": "Background Processor", "type": "backend", "description": "Location-centric background service running every 20 minutes. Fetches surf data from external APIs, processes conditions against user thresholds, and writes results to database. Uses smart endpoint fallback", "size": 1800},
        {"id": "arduino", "name": "Arduino Lamps", "type": "hardware", "description": "Each lamp polls the web server every 13 minutes for its location's surf conditions. LEDs displays surf data. Supports dynamic server discovery via GitHub-hosted config.", "size": 1200},
        {"id": "api", "name": "External APIs", "type": "external", "description": "Third-party weather data providers: OpenWeatherMap, Open-Meteo marine-api subdomain, and Isramar.", "size": 800},
        {"id": "discovery", "name": "ServerDiscovery", "type": "config", "description": "GitHub-hosted configuration system providing dynamic server address lookup.", "size": 300},
        {"id": "mcp_supabase", "name": "MCP Supabase", "type": "tools", "description": "MCP server got interacting with SupaBase via natural language using a LLM client", "size": 800},
        {"id": "mcp_render", "name": "MCP Render", "type": "tools", "description": "MCP server for interacting with render via natural language using a LLM client.", "size": 800},
        {"id": "monitoring", "name": "Monitoring & Insights", "type": "analytics", "description": "uses the MCP server tools to check system health agains configured defaults.", "size": 600}
    ],
    "links": [
        {"source": "api", "target": "processor", "label": "Fetch surf/wind data", "type": "data", "frequency": "20min"},
        {"source": "processor", "target": "database", "label": "Write conditions", "type": "write", "frequency": "20min"},
        {"source": "database", "target": "web", "label": "Serve dashboard data", "type": "read", "frequency": "realtime"},
        {"source": "database", "target": "processor", "label": "Read lamp configs", "type": "read", "frequency": "20min"},
        {"source": "web", "target": "database", "label": "User updates", "type": "write", "frequency": "ondemand"},
        {"source": "web", "target": "redis", "label": "Rate limit check", "type": "check", "frequency": "ondemand"},
        {"source": "discovery", "target": "arduino", "label": "Server address", "type": "config", "frequency": "24h"},
        {"source": "arduino", "target": "web", "label": "Poll lamp data", "type": "read", "frequency": "13min"},
        {"source": "processor", "target": "arduino", "label": "Push (optional)", "type": "write", "frequency": "rare"},
        {"source": "mcp_supabase", "target": "database", "label": "Debug queries", "type": "read", "frequency": "ondemand"},
        {"source": "mcp_render", "target": "web", "label": "Fetch logs/metrics", "type": "monitor", "frequency": "ondemand"},
        {"source": "monitoring", "target": "database", "label": "Analytics queries", "type": "read", "frequency": "daily"},
        {"source": "database", "target": "monitoring", "label": "Store insights", "type": "write", "frequency": "daily"}
    ]
}

# System stats (can be made dynamic with real DB queries)
SYSTEM_STATS = {
    "total_modules": len(SYSTEM_DATA["nodes"]),
    "total_connections": len(SYSTEM_DATA["links"]),
    "architecture_type": "Location-Centric Pull-Based",
    "api_calls_per_cycle": "2-6 (grouped by location)",
    "processor_cycle": "20 minutes",
    "arduino_poll": "13 minutes",
    "data_freshness": "≤ 33 minutes (worst case)"
}

@app.route('/')
def index():
    """Serve the main visualization page"""
    return render_template('index.html')

@app.route('/api/system-data')
def get_system_data():
    """API endpoint for system architecture data"""
    return jsonify(SYSTEM_DATA)

@app.route('/api/stats')
def get_stats():
    """API endpoint for system statistics"""
    return jsonify(SYSTEM_STATS)

@app.route('/api/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({"status": "healthy", "service": "surf-lamp-visualizer"})

@app.route('/sw.js')
def service_worker():
    """Serve service worker from root with correct MIME type for PWA"""
    from flask import send_from_directory
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/manifest.json')
def manifest():
    """Serve manifest from root for PWA"""
    from flask import send_from_directory
    return send_from_directory('static', 'manifest.json', mimetype='application/json')

@app.route('/debug/template')
def debug_template():
    """Debug endpoint to check template rendering"""
    return render_template('index.html')

@app.route('/manpage/<module_id>')
def manpage(module_id):
    """Serve manual page for a specific module"""
    # Security: only allow alphanumeric and underscore
    if not module_id.replace('_', '').isalnum():
        abort(404)

    manpage_path = os.path.join(os.path.dirname(__file__), 'manpages', f'{module_id}.md')

    if not os.path.exists(manpage_path):
        abort(404)

    with open(manpage_path, 'r') as f:
        markdown_content = f.read()

    # Convert markdown to HTML with extras
    html_content = markdown2.markdown(markdown_content, extras=['fenced-code-blocks', 'tables', 'header-ids'])

    # Find module name from SYSTEM_DATA
    module_name = next((node['name'] for node in SYSTEM_DATA['nodes'] if node['id'] == module_id), module_id)

    # Check if extension file exists
    extension_path = os.path.join(os.path.dirname(__file__), 'manpages', 'extensions', f'{module_id}_tools.md')
    has_extension = os.path.exists(extension_path)

    return render_template('manpage.html',
                         content=html_content,
                         module_name=module_name,
                         module_id=module_id,
                         has_extension=has_extension)

@app.route('/manpage/<module_id>/tools')
def manpage_extension(module_id):
    """Serve extension page with tool descriptions"""
    # Security: only allow alphanumeric and underscore
    if not module_id.replace('_', '').isalnum():
        abort(404)

    extension_path = os.path.join(os.path.dirname(__file__), 'manpages', 'extensions', f'{module_id}_tools.md')

    if not os.path.exists(extension_path):
        abort(404)

    with open(extension_path, 'r') as f:
        markdown_content = f.read()

    # Convert markdown to HTML with extras
    html_content = markdown2.markdown(markdown_content, extras=['fenced-code-blocks', 'tables', 'header-ids'])

    # Find module name from SYSTEM_DATA
    module_name = next((node['name'] for node in SYSTEM_DATA['nodes'] if node['id'] == module_id), module_id)

    return render_template('manpage.html',
                         content=html_content,
                         module_name=f"{module_name} - Tools Reference",
                         module_id=module_id,
                         has_extension=False)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
