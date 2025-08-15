# Local Web Memory Extension - Development & Usage Guide

## 📋 Table of Contents
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Usage Guide](#usage-guide)
- [Architecture Overview](#architecture-overview)
- [API Integration](#api-integration)
- [Debugging Guide](#debugging-guide)
- [Common Issues & Solutions](#common-issues--solutions)
- [Testing Checklist](#testing-checklist)

## 🚀 Quick Start

### Prerequisites
1. Chrome browser (version 88+)
2. Backend service running on `http://localhost:8000`
3. Node.js (optional, for development tools)

### Installation Steps
```bash
# 1. Start the backend service (in backend directory)
cd /Users/bytedance/code/newtab/backend
export ARK_API_KEY="16997291-4771-4dc9-9a42-4acc930897fa"
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 2. Load extension in Chrome
# - Open Chrome and go to chrome://extensions/
# - Enable "Developer mode" (toggle in top right)
# - Click "Load unpacked"
# - Select: /Users/bytedance/code/newtab/extension

# 3. Verify installation
# - Extension icon should appear in toolbar
# - New tab should show Local Web Memory interface
```

## 💻 Development Setup

### File Structure
```
extension/
├── manifest.json           # Extension configuration
├── background/
│   └── service-worker.js   # Background tasks, API calls
├── content/
│   └── content-script.js   # Page content extraction
├── newtab/
│   ├── index.html         # New tab UI
│   ├── app.js            # Search functionality
│   └── styles.css        # Styling
├── popup/
│   ├── popup.html        # Toolbar popup
│   ├── popup.js          # Status display
│   └── popup.css         # Popup styling
└── icons/                # Extension icons
```

### Key Files Explained

#### manifest.json
- Defines extension permissions and structure
- Key permissions: `tabs`, `activeTab`, `storage`, `scripting`
- Host permission for `http://localhost:8000/*`

#### service-worker.js
- Handles all backend API communication
- Manages indexing queue and retry logic
- Stores settings in `chrome.storage.local`
- Message handler for content script and popup

#### content-script.js
- Runs on every webpage (except chrome://)
- Extracts main content intelligently
- Sends data to service worker for indexing
- Skips pages with < 100 characters

#### newtab/app.js
- Provides search interface
- Handles both keyword and semantic search
- Manages settings and domain exclusions
- Real-time search with debouncing

## 📖 Usage Guide

### Basic Usage

#### 1. Automatic Indexing
- Simply browse the web normally
- Pages are automatically indexed in the background
- Small badge appears on extension icon when indexing

#### 2. Searching Your History
- Open a new tab
- Type search query in the search box
- Choose search mode:
  - **Keyword Search**: Exact term matching
  - **Semantic Search**: Meaning-based matching
- Click results to open pages

#### 3. Managing Privacy
- Click settings icon (⚙️) in new tab
- Add domains to exclude from indexing
- Toggle indexing on/off
- Clear all data when needed

### Advanced Features

#### Domain Exclusions
```javascript
// Domains can be excluded via settings panel
// Format: example.com (without http://)
// Applies to all subdomains automatically
```

#### Data Export
- Settings → Data Management → Export Data
- Creates JSON file with all indexed pages
- Includes metadata and settings

#### Keyboard Shortcuts
- `Enter` - Execute search
- `Esc` - Close settings panel
- Focus automatically on search box in new tab

### Extension Popup Features
- **Status Indicators**:
  - 🟢 Backend Online - System operational
  - 🔴 Backend Offline - Check backend service
  - 📊 Pages Indexed - Total count
  - ⏱️ Last Indexed - Time since last page

## 🏗️ Architecture Overview

### Data Flow
```
1. User visits webpage
   ↓
2. Content Script extracts content
   ↓
3. Service Worker receives data
   ↓
4. Backend API indexes with AI
   ↓
5. User searches in new tab
   ↓
6. Results retrieved from backend
```

### Storage Architecture
- **chrome.storage.local**: Extension settings
  - Indexing enabled/disabled
  - Excluded domains list
  - Statistics
- **Backend SQLite**: Page content and metadata
- **Backend Vector Store**: Semantic embeddings

### Message Passing
```javascript
// Content → Service Worker
chrome.runtime.sendMessage({
  type: 'INDEX_PAGE',
  data: { url, title, content }
})

// Popup → Service Worker
chrome.runtime.sendMessage({
  type: 'GET_STATUS'
})

// New Tab → Service Worker
chrome.runtime.sendMessage({
  type: 'SEARCH',
  query: 'search terms',
  searchType: 'keyword'
})
```

## 🔌 API Integration

### Backend Endpoints Used

```javascript
// Index a page
POST http://localhost:8000/index
Body: { url, title, content, favicon_url }

// Search pages
GET http://localhost:8000/search/keyword?q=query
GET http://localhost:8000/search/vector?q=query

// Manage pages
GET http://localhost:8000/pages
GET http://localhost:8000/pages/{id}
DELETE http://localhost:8000/pages/{id}

// System status
GET http://localhost:8000/health
GET http://localhost:8000/stats
```

### Error Handling
- Automatic retry with exponential backoff
- Graceful degradation when backend offline
- User-friendly error messages
- Console logging for debugging

## 🐛 Debugging Guide

### Chrome DevTools Access

#### Service Worker Debugging
1. Go to `chrome://extensions/`
2. Find "Local Web Memory"
3. Click "Details"
4. Click "Service Worker" link
5. DevTools opens with service worker context

#### Content Script Debugging
1. Visit any webpage
2. Open DevTools (F12)
3. Console shows content script logs
4. Sources → Content Scripts → extension files

#### New Tab Debugging
1. Open new tab
2. Open DevTools (F12)
3. Full debugging available

### Common Debug Commands

```javascript
// In service worker console
chrome.storage.local.get('localWebMemory', console.log)

// Check indexing status
chrome.runtime.sendMessage({type: 'GET_STATUS'}, console.log)

// Manual index trigger (in content script console)
processPage()

// Test search (in new tab console)
handleSearch()
```

### Logging Locations
- **Service Worker**: `chrome://serviceworker-internals/`
- **Extension Errors**: `chrome://extensions/` → Errors button
- **Network Requests**: DevTools → Network tab
- **Storage Inspector**: DevTools → Application → Storage

## 🔧 Common Issues & Solutions

### Issue: Pages Not Being Indexed

**Symptoms**: No increase in indexed page count

**Solutions**:
1. Check backend is running: `curl http://localhost:8000/health`
2. Verify indexing enabled in popup
3. Check domain not in exclusion list
4. View service worker logs for errors
5. Ensure page has > 100 characters of content

### Issue: Search Returns No Results

**Symptoms**: Empty results despite indexed pages

**Solutions**:
1. Try both search modes (keyword/semantic)
2. Check backend connection status
3. Verify pages are actually indexed: `curl http://localhost:8000/pages`
4. Check for JavaScript errors in new tab console

### Issue: Extension Icon Missing

**Symptoms**: No extension icon in toolbar

**Solutions**:
1. Check extension is enabled in `chrome://extensions/`
2. Pin extension: Click puzzle piece → Pin "Local Web Memory"
3. Reload extension: Disable and re-enable
4. Check for manifest errors in extension page

### Issue: Backend Connection Failed

**Symptoms**: "Backend Offline" status

**Solutions**:
1. Verify backend running: `lsof -i :8000`
2. Check CORS enabled in backend
3. No firewall blocking localhost:8000
4. Try accessing `http://localhost:8000/docs` directly

## ✅ Testing Checklist

### Installation Testing
- [ ] Extension loads without errors
- [ ] Icon appears in toolbar
- [ ] Popup opens when clicked
- [ ] New tab override works

### Indexing Testing
- [ ] Visit a webpage → Check indexed
- [ ] Visit chrome:// page → Should skip
- [ ] Visit excluded domain → Should skip
- [ ] Toggle indexing off → Should stop
- [ ] Check rate limiting works

### Search Testing
- [ ] Keyword search returns results
- [ ] Semantic search returns results
- [ ] Real-time search works
- [ ] Results are clickable
- [ ] Delete button works

### Settings Testing
- [ ] Add domain exclusion works
- [ ] Remove domain exclusion works
- [ ] Clear all data works
- [ ] Export data creates valid JSON
- [ ] Settings persist after restart

### Error Handling Testing
- [ ] Backend offline → Graceful failure
- [ ] Invalid domain → Error message
- [ ] Network timeout → Retry logic
- [ ] Malformed page → Skips gracefully

## 📊 Performance Metrics

### Target Performance
- Page indexing: < 2 seconds
- Search response: < 500ms
- Content extraction: < 100ms
- UI interactions: < 50ms

### Memory Usage
- Service worker: ~10-20MB
- Content script: ~5MB per page
- New tab page: ~15-30MB

### Storage Limits
- chrome.storage.local: 10MB
- Backend SQLite: Unlimited
- Recommended max pages: 10,000

## 🚢 Deployment Considerations

### For Distribution
1. Update manifest version number
2. Create production icons (16, 48, 128px)
3. Remove console.log statements
4. Minify JavaScript files
5. Create ZIP for Chrome Web Store

### Security Checklist
- [ ] No hardcoded API keys
- [ ] HTTPS only in production
- [ ] Content Security Policy set
- [ ] Input validation on all forms
- [ ] XSS protection in result display

## 📚 Additional Resources

### Chrome Extension Documentation
- [Manifest V3 Guide](https://developer.chrome.com/docs/extensions/mv3/)
- [Service Workers](https://developer.chrome.com/docs/extensions/mv3/service_workers/)
- [Content Scripts](https://developer.chrome.com/docs/extensions/mv3/content_scripts/)
- [Chrome Storage API](https://developer.chrome.com/docs/extensions/reference/storage/)

### Project Specific
- Backend API Docs: http://localhost:8000/docs
- Main PRD: `/Users/bytedance/code/newtab/prd.md`
- Backend Implementation: `/Users/bytedance/code/newtab/backend/README.md`

## 🤝 Contributing

### Development Workflow
1. Create feature branch
2. Make changes
3. Test thoroughly using checklist
4. Update documentation
5. Submit for review

### Code Style
- Use consistent indentation (2 spaces)
- Comment complex logic
- Keep functions small and focused
- Handle errors gracefully
- Log important events

---

**Last Updated**: January 2025
**Version**: 1.0.0
**Author**: Local Web Memory Team