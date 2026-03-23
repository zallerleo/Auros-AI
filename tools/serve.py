import http.server
import socketserver
import os

os.chdir(os.path.join(os.path.dirname(__file__), "portfolio", "client_the_imagine_team"))

PORT = 8080
Handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving at http://localhost:{PORT}")
    httpd.serve_forever()