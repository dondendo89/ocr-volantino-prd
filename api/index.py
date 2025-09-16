import json
import os
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
                "admin_url": "/admin",
                "docs": "/docs"
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
        elif path == '/health':
            response = {
                "status": "healthy",
                "message": "API funzionante correttamente",
                "timestamp": datetime.now().isoformat(),
                "environment": "vercel"
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
        elif path == '/api/status':
            response = {
                "api_version": "1.0.0",
                "platform": "vercel",
                "status": "operational",
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
        elif path == '/admin' or path == '/admin/':
            # Serve la pagina admin
            try:
                # Cerca il file admin.html nella directory static
                static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
                admin_file = os.path.join(static_dir, 'admin.html')
                
                if os.path.exists(admin_file):
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    with open(admin_file, 'r', encoding='utf-8') as f:
                        self.wfile.write(f.read().encode('utf-8'))
                else:
                    response = {
                        "error": "File admin.html non trovato",
                        "path": admin_file,
                        "timestamp": datetime.now().isoformat()
                    }
                    self.wfile.write(json.dumps(response, indent=2).encode())
            except Exception as e:
                response = {
                    "error": f"Errore nel caricamento admin: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
                self.wfile.write(json.dumps(response, indent=2).encode())
        else:
            response = {
                "error": "Endpoint non trovato",
                "path": path,
                "available_endpoints": ["/", "/health", "/api/status", "/admin"],
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()