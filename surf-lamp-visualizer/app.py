"""
Surf Lamp System Visualization Server
Serves interactive D3.js visualization of system architecture
"""
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# System architecture data
SYSTEM_DATA = {
    "nodes": [
        {"id": "web", "name": "Web Application", "type": "backend", "description": "Flask app serving user dashboard", "size": 1500},
        {"id": "database", "name": "Database (Supabase)", "type": "storage", "description": "PostgreSQL with user data, lamp configs, conditions", "size": 2000},
        {"id": "redis", "name": "Redis Cache", "type": "storage", "description": "Rate limiting for user actions", "size": 500},
        {"id": "processor", "name": "Background Processor", "type": "backend", "description": "Fetches surf data every 20 minutes", "size": 1800},
        {"id": "arduino", "name": "Arduino Lamps", "type": "hardware", "description": "ESP32 with LED strips polling every 13 min", "size": 1200},
        {"id": "api", "name": "External APIs", "type": "external", "description": "OpenWeatherMap, Isramar, Open-Meteo", "size": 800},
        {"id": "discovery", "name": "ServerDiscovery", "type": "config", "description": "GitHub-hosted config.json for dynamic server lookup", "size": 300},
        {"id": "mcp_supabase", "name": "MCP Supabase", "type": "tools", "description": "Database debugging tools for Claude", "size": 600},
        {"id": "mcp_render", "name": "MCP Render", "type": "tools", "description": "Production monitoring and logs", "size": 700},
        {"id": "monitoring", "name": "Monitoring & Insights", "type": "analytics", "description": "System health and usage analytics", "size": 900}
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)