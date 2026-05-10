"""
Simple HTTP server with API proxy for IP-Creator frontend
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request
import urllib.error
import json
import os

class ProxyHandler(SimpleHTTPRequestHandler):
    """HTTP handler with API proxy support"""
    
    def __init__(self, *args, **kwargs):
        self.api_url = 'http://localhost:8000'
        super().__init__(*args, directory='frontend-vue/dist', **kwargs)
    
    def do_GET(self):
        # Proxy API requests to backend
        if self.path.startswith('/api/'):
            self._proxy_request('GET')
        else:
            # Serve static files
            if self.path == '/' or self.path == '/index.html':
                self.path = '/index.html'
            super().do_GET()
    
    def do_POST(self):
        if self.path.startswith('/api/'):
            self._proxy_request('POST')
        else:
            self.send_error(404)
    
    def _proxy_request(self, method):
        """Proxy request to backend API"""
        try:
            # Get request body for POST
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None
            
            # Create request
            url = f"{self.api_url}{self.path}"
            req = urllib.request.Request(url, data=body, method=method)
            
            # Copy headers
            for key, value in self.headers.items():
                if key.lower() not in ['host', 'content-length']:
                    req.add_header(key, value)
            
            # Send request
            with urllib.request.urlopen(req, timeout=30) as response:
                # Send response
                self.send_response(response.status)
                for key, value in response.getheaders():
                    if key.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(key, value)
                self.end_headers()
                
                # Write body
                if method == 'GET':
                    self.wfile.write(response.read())
                else:
                    self.wfile.write(b'{}')
                    
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_error(500, str(e))
    
    def end_headers(self):
        """Add CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.end_headers()

def run_server(port=80):
    """Start the server"""
    server = HTTPServer(('0.0.0.0', port), ProxyHandler)
    print(f"Server running on http://localhost:{port}")
    print(f"API proxy: http://localhost:8000")
    print("Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()

if __name__ == '__main__':
    run_server(80)
