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
CORS(app)

# System architecture data
SYSTEM_DATA = {
    "nodes": [
        {"id": "web", "name": "Web Application", "type": "backend", "description": "Flask-based web server serving the user dashboard at surflampz.com. Handles user authentication, lamp management, threshold configuration, and real-time surf condition display. Users can update their preferences which trigger Redis rate limiting checks before database writes.", "size": 1500},
        {"id": "database", "name": "Database (Supabase)", "type": "storage", "description": "PostgreSQL database hosted on Supabase storing all system data. Contains tables for users, lamps (with Arduino IDs and IPs), current_conditions (wave height, period, wind speed/direction), daily_usage tracking, and location_websites mapping. Serves as the central source of truth for the entire system.", "size": 2000},
        {"id": "redis", "name": "Redis Cache", "type": "storage", "description": "In-memory cache service providing rate limiting for user actions. Prevents API abuse by limiting how frequently users can change locations, modify thresholds, or update preferences. Protects weather API quotas and maintains system stability by blocking rapid successive changes.", "size": 500},
        {"id": "processor", "name": "Background Processor", "type": "backend", "description": "Location-centric background service running every 20 minutes on Render. Groups lamps by location to minimize API calls (2-6 per cycle instead of per-lamp). Fetches surf data from external APIs, processes conditions against user thresholds, and writes results to database. Uses smart endpoint fallback (OpenWeatherMap for wind, Open-Meteo marine API for waves).", "size": 1800},
        {"id": "arduino", "name": "Arduino Lamps", "type": "hardware", "description": "ESP32 microcontrollers with WS2812B LED strips running Arduino code. Each lamp polls the web server every 13 minutes for its location's surf conditions. LEDs display color-coded surf quality (5 themes available) with special nighttime behavior showing only top LEDs. Supports dynamic server discovery via GitHub-hosted config.", "size": 1200},
        {"id": "api", "name": "External APIs", "type": "external", "description": "Third-party weather data providers: OpenWeatherMap (wind speed/direction), Open-Meteo marine-api subdomain (wave height/period), and Isramar (Israel-specific surf data). System uses hybrid approach after resolving rate limiting issues - marine-api.open-meteo.com for waves, OpenWeatherMap for wind data.", "size": 800},
        {"id": "discovery", "name": "ServerDiscovery", "type": "config", "description": "GitHub-hosted configuration system (surflamp-discovery repo) providing dynamic server address lookup. Arduino lamps fetch config.json every 24 hours to get current server URL, enabling zero-downtime server migrations and eliminating need to reflash Arduinos when deployment URLs change.", "size": 300},
        {"id": "mcp_supabase", "name": "MCP Supabase", "type": "tools", "description": "Model Context Protocol server providing Claude AI with direct database access for debugging. Offers specialized tools for querying tables, analyzing surf conditions by location, monitoring lamp status, searching users, and generating dashboard data. Built with FastMCP for robust async operations.", "size": 600},
        {"id": "mcp_render", "name": "MCP Render", "type": "tools", "description": "MCP server for production monitoring and debugging via Render API. Provides Claude with tools to fetch service logs, search for errors, analyze deployments, check service health, and monitor metrics (CPU, memory, HTTP requests). Essential for real-time debugging of timeout issues, rate limiting, and deployment failures.", "size": 700},
        {"id": "monitoring", "name": "Monitoring & Insights", "type": "analytics", "description": "System health monitoring and usage analytics combining Render metrics, database queries, and service logs. Tracks deployment history, API call patterns, user activity, lamp connectivity, and overall system performance. Helps identify trends, optimize resource usage, and maintain service reliability.", "size": 900}
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

    # Find module info from SYSTEM_DATA
    module_node = next((node for node in SYSTEM_DATA['nodes'] if node['id'] == module_id), None)
    module_name = module_node['name'] if module_node else module_id
    module_type = module_node['type'] if module_node else 'unknown'

    return render_template('manpage.html',
                         content=html_content,
                         module_name=module_name,
                         module_id=module_id,
                         module_type=module_type)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)