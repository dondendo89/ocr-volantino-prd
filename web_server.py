#!/usr/bin/env python3
"""
Semplice server web per servire l'interfaccia di visualizzazione prodotti
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handler HTTP con supporto CORS per permettere chiamate API"""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def main():
    # Porta per il server web
    PORT = 3000
    
    # Directory statica
    static_dir = Path(__file__).parent / "static"
    
    if not static_dir.exists():
        print(f"❌ Directory statica non trovata: {static_dir}")
        sys.exit(1)
    
    # Cambia nella directory statica
    os.chdir(static_dir)
    
    # Crea il server
    with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
        print(f"🌐 Server web avviato su http://localhost:{PORT}")
        print(f"📁 Servendo file da: {static_dir}")
        print("\n🔗 Apri nel browser: http://localhost:3000")
        print("\n⚠️  Assicurati che l'API sia in esecuzione su http://localhost:8000")
        print("\n🛑 Premi Ctrl+C per fermare il server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server fermato")

if __name__ == "__main__":
    main()