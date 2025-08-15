#!/usr/bin/env python3
"""
Simple test server for the Local Web Memory Chrome extension.
Serves the extension files and test page for local development.
"""

import http.server
import socketserver
import os
import sys
import json
from pathlib import Path

PORT = 8081
EXTENSION_DIR = Path(__file__).parent.parent / "extension"
TEST_DIR = Path(__file__).parent

class ExtensionTestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for serving extension files and test pages."""
    
    def __init__(self, *args, **kwargs):
        # Set the directory to serve from
        super().__init__(*args, directory=str(TEST_DIR.parent), **kwargs)
    
    def do_GET(self):
        """Handle GET requests with proper CORS headers."""
        # Add CORS headers for extension testing
        self.send_response(200)
        
        # Determine content type based on file extension
        if self.path.endswith('.js'):
            self.send_header('Content-Type', 'application/javascript')
        elif self.path.endswith('.html'):
            self.send_header('Content-Type', 'text/html')
        elif self.path.endswith('.css'):
            self.send_header('Content-Type', 'text/css')
        elif self.path.endswith('.json'):
            self.send_header('Content-Type', 'application/json')
        
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        
        # Serve the file
        return super().do_GET()
    
    def log_message(self, format, *args):
        """Custom log format."""
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")

def main():
    """Run the test server."""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║        Local Web Memory Extension - Test Server              ║
╚══════════════════════════════════════════════════════════════╝

📁 Serving from: {TEST_DIR.parent}
🌐 Server running at: http://localhost:{PORT}

📋 Available test pages:
   • http://localhost:{PORT}/test/test-extension.html - Full test interface
   • http://localhost:{PORT}/extension/newtab/index.html - Extension new tab page
   • http://localhost:{PORT}/extension/popup/popup.html - Extension popup

🧪 Quick Test Steps:
   1. Make sure backend is running at http://localhost:8000
   2. Open http://localhost:{PORT}/test/test-extension.html
   3. Click "Run All Tests" to validate the backend
   4. Try searching for content

🔧 Chrome Extension Testing:
   1. Open Chrome and go to chrome://extensions
   2. Enable "Developer mode" (top right)
   3. Click "Load unpacked"
   4. Select the "{EXTENSION_DIR}" folder
   5. Open a new tab to see the extension in action

⚠️  Note: Make sure the backend server is running:
   cd backend && source .venv/bin/activate && uvicorn main:app --reload

Press Ctrl+C to stop the server.
""")
    
    try:
        with socketserver.TCPServer(("", PORT), ExtensionTestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✋ Server stopped.")
        sys.exit(0)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n❌ Error: Port {PORT} is already in use.")
            print("   Try stopping other servers or use a different port.")
        else:
            print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()