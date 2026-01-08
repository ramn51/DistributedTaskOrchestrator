#  Copyright 2026 Ram Narayanan
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.

from http.server import BaseHTTPRequestHandler, HTTPServer
import sys

PORT = 9000

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.wfile.write(b"Titan Comprehensive Test: SUCCESS")

print(f"[SERVER] Starting Test Server on {PORT}...")
sys.stdout.flush()

httpd = HTTPServer(('0.0.0.0', PORT), Handler)
httpd.serve_forever()