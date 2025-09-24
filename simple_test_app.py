#!/usr/bin/env python3
"""
Simple test web app for Render API deployment testing
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import json
from datetime import datetime

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        html = f"""
        <html>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h1>🎉 API Deployment Test Success!</h1>
            <p><strong>Deployed via Render API</strong></p>
            <p>Service: {os.getenv('SERVICE_NAME', 'test-api-service')}</p>
            <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Environment: {os.getenv('TEST_ENV', 'development')}</p>
            <hr>
            <p style="color: green;">✅ MCP Render API deployment tools working!</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        # Suppress default logging to avoid cluttering Render logs
        pass

def main():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), TestHandler)
    print(f"🚀 Test server starting on port {port}")
    server.serve_forever()

if __name__ == '__main__':
    main()