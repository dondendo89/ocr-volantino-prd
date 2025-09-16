import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Headers CORS
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        # Routing semplice
        if path == '/' or path == '':
            response = {
                "message": "OCR Volantino API - Versione Vercel",
                "status": "active",
                "timestamp": datetime.now().isoformat(),
                "docs": "/docs"
            }
        elif path == '/health':
            response = {
                "status": "healthy",
                "message": "API funzionante correttamente",
                "timestamp": datetime.now().isoformat(),
                "environment": "vercel"
            }
        elif path == '/api/status':
            response = {
                "api_version": "1.0.0",
                "platform": "vercel",
                "status": "operational",
                "timestamp": datetime.now().isoformat()
            }
        else:
            response = {
                "error": "Endpoint non trovato",
                "path": path,
                "timestamp": datetime.now().isoformat()
            }
        
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()