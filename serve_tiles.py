from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import re

class TileRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        super().end_headers()

if __name__ == '__main__':
    os.chdir('output/tiles')  # Move into tiles directory
    httpd = HTTPServer(('localhost', 3002), TileRequestHandler)
    print("Serving tiles at http://localhost:3002")
    httpd.serve_forever()

