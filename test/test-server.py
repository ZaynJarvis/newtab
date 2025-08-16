#!/usr/bin/env python3
"""
Debug wrapper server for the New Tab Chrome extension.
Serves as a wrapper around the newtab page for debugging purposes.
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
    """Custom handler that primarily serves the newtab page for debugging."""
    
    def __init__(self, *args, **kwargs):
        # Set the directory to serve from
        super().__init__(*args, directory=str(TEST_DIR.parent), **kwargs)
    
    def do_GET(self):
        """Handle GET requests, redirecting root to newtab page."""
        # Redirect root path to newtab page for debugging
        if self.path == '/' or self.path == '':
            self.send_response(301)
            self.send_header('Location', '/extension/newtab/index.html')
            self.end_headers()
            return
        
        # Add CORS headers for extension testing
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        
        # Determine content type based on file extension
        if self.path.endswith('.js'):
            self.send_header('Content-Type', 'application/javascript')
        elif self.path.endswith('.html'):
            self.send_header('Content-Type', 'text/html')
        elif self.path.endswith('.css'):
            self.send_header('Content-Type', 'text/css')
        elif self.path.endswith('.json'):
            self.send_header('Content-Type', 'application/json')
        
        self.end_headers()
        
        # Serve the file
        return super().do_GET()
    
    def log_message(self, format, *args):
        """Custom log format."""
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")

def main():
    """Run the debug wrapper server."""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║        New Tab Extension - Debug Wrapper            ║
╚══════════════════════════════════════════════════════════════╝

📁 Serving from: {TEST_DIR.parent}
🌐 Debug server running at: http://localhost:{PORT}

🐛 Debug Access:
   • http://localhost:{PORT}/ - Direct access to newtab page (auto-redirected)
   • http://localhost:{PORT}/extension/newtab/index.html - Newtab page
   
📋 Other test pages:
   • http://localhost:{PORT}/test/test-extension.html - Full test interface
   • http://localhost:{PORT}/extension/popup/popup.html - Extension popup

🧪 Debug Workflow:
   1. Make sure backend is running at http://localhost:8000
   2. Open http://localhost:{PORT}/ for direct newtab debugging
   3. Use browser dev tools to inspect metadata panel issues
   4. Check network tab for failed requests

🔧 For Chrome Extension Testing:
   1. Open Chrome and go to chrome://extensions
   2. Enable "Developer mode" (top right)
   3. Click "Load unpacked"
   4. Select the "{EXTENSION_DIR}" folder
   5. Open a new tab to see the extension in action

⚠️  Note: Make sure the backend server is running:
   cd backend && uv run uvicorn main:app --reload

Press Ctrl+C to stop the debug server.
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