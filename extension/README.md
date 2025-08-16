# New Tab Chrome Extension

A privacy-first Chrome extension that automatically indexes visited web pages locally with AI-powered keywords and provides instant semantic search from your new tab.

## Features

- 🔍 **Dual Search Modes**: Keyword search (BM25) and semantic search (vector embeddings)
- 🤖 **AI-Powered**: Automatic keyword and description generation via ByteDance Ark LLM
- 🔒 **Privacy First**: All data stored locally, no cloud sync
- ⚡ **Fast Search**: Sub-second search across your entire browsing history
- 🎨 **Beautiful UI**: Clean, modern interface in new tab
- ⚙️ **Full Control**: Domain exclusions, data export, clear all data

## Installation

1. Make sure the backend is running:
   ```bash
   cd ../backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Load the extension in Chrome:
   - Open Chrome and navigate to `chrome://extensions/`
   - Enable "Developer mode" (top right)
   - Click "Load unpacked"
   - Select the `extension` directory

3. The extension will automatically start indexing pages you visit

## Usage

### Searching Your History
- Open a new tab
- Type your search query
- Choose between "Keyword Search" or "Semantic Search"
- Click on results to open pages

### Managing Settings
- Click the settings icon (⚙️) in the new tab
- Configure:
  - Enable/disable indexing
  - Add excluded domains
  - Clear all data
  - Export your data

### Viewing Status
- Click the extension icon in toolbar to see:
  - Backend connection status
  - Total pages indexed
  - Last indexed page
  - Quick access to search

## Architecture

```
extension/
├── manifest.json          # Chrome Extension Manifest V3
├── background/
│   └── service-worker.js  # Handles API calls and indexing
├── content/
│   └── content-script.js  # Extracts page content
├── newtab/
│   ├── index.html        # New tab override UI
│   ├── app.js           # Search and settings logic
│   └── styles.css       # Styling
└── popup/
    ├── popup.html       # Extension popup
    ├── popup.js         # Status display
    └── popup.css        # Popup styling
```

## How It Works

1. **Content Extraction**: When you visit a page, the content script extracts the main content
2. **Background Processing**: Service worker sends content to backend API
3. **AI Processing**: Backend generates keywords and embeddings using ByteDance Ark
4. **Local Storage**: Data is indexed in SQLite (keywords) and vector store (embeddings)
5. **Instant Search**: New tab interface queries the backend for results

## Privacy

- ✅ All data stored locally on your machine
- ✅ No cloud sync or external storage
- ✅ Content sent only to local backend (localhost:8000)
- ✅ Full control over what gets indexed
- ✅ Easy data deletion and export

## Development

### Testing
```bash
# Check if backend is running
curl http://localhost:8000/health

# View indexed pages
curl http://localhost:8000/pages

# Test search
curl "http://localhost:8000/search/keyword?q=test"
```

### Debugging
- Open Chrome DevTools on any tab
- Check Service Worker logs: chrome://extensions/ → Details → Service Worker
- Check Content Script logs: Regular DevTools console on web pages
- Check New Tab logs: DevTools on new tab page

## Troubleshooting

### Extension not indexing pages
1. Check backend is running: `http://localhost:8000/health`
2. Check indexing is enabled in popup or settings
3. Check domain is not excluded
4. View Service Worker logs for errors

### Search not working
1. Verify backend connection in popup status
2. Check if pages have been indexed
3. Try both keyword and semantic search modes
4. Check browser console for errors

### Backend connection issues
1. Ensure backend is running on port 8000
2. Check CORS is enabled in backend
3. Verify no firewall blocking localhost:8000

## License

MIT