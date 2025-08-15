# Local Web Memory Extension - Testing Guide

## Overview
This guide documents how to test the Local Web Memory Chrome extension locally without publishing it to the Chrome Web Store.

## Prerequisites
1. Backend server running at `http://localhost:8000`
2. Python 3.8+ installed
3. Chrome browser

## Testing Methods

### Method 1: Load Extension in Chrome Developer Mode

This is the standard way to test a Chrome extension locally:

1. **Open Chrome Extensions Page**
   - Navigate to `chrome://extensions`
   - Or click the puzzle icon → "Manage Extensions"

2. **Enable Developer Mode**
   - Toggle the "Developer mode" switch in the top-right corner

3. **Load the Extension**
   - Click "Load unpacked"
   - Navigate to `/Users/bytedance/code/newtab/extension`
   - Click "Select"

4. **Test the Extension**
   - Open a new tab - you should see the custom new tab page
   - Browse any website and it will be automatically indexed
   - Search for content using the new tab interface

5. **Reload Changes**
   - After making code changes, click the refresh icon on the extension card
   - Or click "Update" button at the top of the extensions page

### Method 2: Standalone Test Page

Use the test HTML page to test the backend API without loading the extension:

1. **Start the Test Server**
   ```bash
   cd /Users/bytedance/code/newtab/test
   python3 test-server.py
   ```

2. **Open Test Interface**
   - Navigate to `http://localhost:8080/test/test-extension.html`

3. **Available Test Actions**
   - **Health Check**: Verify backend is running
   - **Get Statistics**: View indexed pages count
   - **Index Test Page**: Add a sample page to the database
   - **Test Keyword Search**: Search using full-text search
   - **Test Vector Search**: Search using semantic similarity
   - **List All Pages**: View all indexed pages
   - **Run All Tests**: Execute all tests sequentially

### Method 3: Direct File Access

For quick testing without a server:

1. **Open the Test Page Directly**
   ```bash
   open /Users/bytedance/code/newtab/test/test-extension.html
   ```
   
2. **Note**: This method works for API testing but not for testing the full extension features

### Method 4: Backend API Testing

Test the backend directly using the quick test script:

```bash
cd /Users/bytedance/code/newtab/demo
python3 quick-test.py
```

## Troubleshooting

### 422 Error Fixed
The 422 Unprocessable Entity error has been fixed by updating the query parameter from `q` to `query` in the service worker.

### Common Issues

1. **Backend Not Running**
   - Error: "Backend connection failed"
   - Solution: Start the backend server
   ```bash
   cd backend
   source .venv/bin/activate
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Extension Not Updating**
   - Issue: Changes not reflected after code modification
   - Solution: Click the refresh icon on the extension card in `chrome://extensions`

3. **CORS Errors**
   - Issue: Cross-origin requests blocked
   - Solution: The backend already has CORS configured for `chrome-extension://*`

4. **Port Already in Use**
   - Error: "Address already in use"
   - Solution: Stop other servers or change the port in test-server.py

## Test Workflow

1. **Start Backend Server**
   ```bash
   cd backend
   source .venv/bin/activate
   export ARK_API_KEY="your-api-key"  # Optional for AI features
   uvicorn main:app --reload
   ```

2. **Start Test Server** (Optional)
   ```bash
   cd test
   python3 test-server.py
   ```

3. **Load Extension in Chrome**
   - Follow Method 1 above

4. **Run Tests**
   - Use the test interface to validate functionality
   - Check console for detailed logs

5. **Monitor Backend Logs**
   - Watch the terminal running uvicorn for request logs
   - Look for any errors or 422 responses

## API Endpoints Reference

- `GET /health` - Health check
- `GET /stats` - System statistics
- `POST /index` - Index a new page
- `GET /search/keyword?query=...` - Keyword search
- `GET /search/vector?query=...` - Semantic search
- `GET /pages` - List all pages
- `DELETE /pages/{id}` - Delete a specific page

## Console Commands

Open Chrome DevTools Console (F12) on the new tab page:

```javascript
// Check backend status
fetch('http://localhost:8000/health').then(r => r.json()).then(console.log)

// Perform search
fetch('http://localhost:8000/search/keyword?query=python&limit=5')
  .then(r => r.json()).then(console.log)

// Get statistics
fetch('http://localhost:8000/stats').then(r => r.json()).then(console.log)
```

## Development Tips

1. **Use the Console**: The test interface logs all actions to the console for debugging
2. **Check Network Tab**: Use Chrome DevTools Network tab to inspect API calls
3. **Test Incrementally**: Test each feature separately before running all tests
4. **Monitor Both Logs**: Keep both backend and frontend logs visible

## Success Indicators

✅ Backend health check returns "healthy"
✅ No 422 errors in the backend logs
✅ Search queries return results
✅ Pages can be indexed and retrieved
✅ Extension icon appears in Chrome toolbar
✅ New tab page loads with search interface