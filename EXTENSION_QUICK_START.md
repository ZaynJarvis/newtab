# 🚀 Local Web Memory Extension - Quick Start Guide

## Installation in 3 Minutes

### Step 1: Start Backend (30 seconds)
```bash
cd /Users/bytedance/code/newtab/backend
export ARK_API_KEY="16997291-4771-4dc9-9a42-4acc930897fa"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
✅ Backend ready when you see: `Uvicorn running on http://0.0.0.0:8000`

### Step 2: Install Extension (1 minute)
1. Open Chrome
2. Go to `chrome://extensions/`
3. Enable **"Developer mode"** (top right toggle)
4. Click **"Load unpacked"**
5. Select folder: `/Users/bytedance/code/newtab/extension`

✅ Extension installed when you see the extension card appear

### Step 3: Start Using (30 seconds)
1. **Pin the extension**: Click puzzle piece icon → Pin "Local Web Memory"
2. **Visit any webpage** - it will auto-index in the background
3. **Open a new tab** - you'll see the search interface
4. **Search your history** - type anything you remember!

---

## 🎯 Essential Features

### Search Your History
- **New Tab**: Beautiful search interface
- **Two Modes**: 
  - 🔍 Keyword Search (exact matching)
  - 🧠 Semantic Search (AI-powered)

### Control Privacy
- **Extension Icon** → See status
- **Settings** (⚙️ in new tab) → Exclude domains
- **Clear Data** → Remove everything instantly

### Quick Keyboard Shortcuts
- `Ctrl+T` / `Cmd+T` - Open search (new tab)
- `Enter` - Search
- Type immediately in new tab (auto-focus)

---

## 📊 Status Indicators

### Extension Icon Badge
- ✅ **Green checkmark** - Page indexed successfully
- ⚠️ **Red exclamation** - Indexing error
- 📊 **Number** - Pages being processed

### Popup Status
Click extension icon to see:
- 🟢 **Backend Online** - Everything working
- 🔴 **Backend Offline** - Check backend service
- 📈 **Pages Indexed** - Your collection size

---

## 🔥 Power User Tips

### 1. Smart Domain Exclusions
```
Settings → Excluded Domains
Add: github.com (excludes all GitHub)
Add: *.google.com (excludes all Google)
```

### 2. Semantic Search Examples
Instead of exact keywords, try concepts:
- "that article about machine learning"
- "the documentation I read yesterday"
- "pricing comparison pages"

### 3. Quick Data Management
- **Export**: Settings → Export Data (JSON backup)
- **Clear**: Settings → Clear All Data (fresh start)
- **Toggle**: Extension icon → Toggle indexing on/off

### 4. Debug Mode
See what's happening behind the scenes:
```javascript
// In new tab console
localStorage.debug = 'true'
// Now see detailed logs
```

---

## 🚨 Troubleshooting

### Nothing is being indexed?
1. Check backend: Visit http://localhost:8000/docs
2. Check popup: Is indexing enabled?
3. Check domain: Is it excluded?

### Search not working?
1. Have you visited any pages yet?
2. Try both search modes
3. Check backend status in popup

### Extension not appearing?
1. Is developer mode on?
2. Try reloading: chrome://extensions → Reload
3. Check for errors: Details → Errors

---

## 📈 What Gets Indexed

### ✅ Indexed
- Regular websites (https://, http://)
- Articles, blogs, documentation
- Dynamic web apps
- Search results pages

### ❌ Not Indexed
- Chrome pages (chrome://)
- Extension pages (chrome-extension://)
- Local files (file://)
- Pages < 100 characters
- Excluded domains

---

## 🎨 Interface Overview

### New Tab Components
```
┌─────────────────────────────────────┐
│      Local Web Memory               │ <- Click for home
│   [🔍 Search bar............] [→]   │ <- Type & Enter
│   ○ Keyword  ○ Semantic            │ <- Search modes
├─────────────────────────────────────┤
│   📄 Result 1                       │ <- Click to open
│   📄 Result 2                       │
│   📄 Result 3                       │
├─────────────────────────────────────┤
│  Pages: 156  |  Status: Online  ⚙️  │ <- Stats & Settings
└─────────────────────────────────────┘
```

### Popup Components
```
┌──────────────────────┐
│  Local Web Memory    │
│  [🟢] Indexing On    │ <- Toggle
├──────────────────────┤
│  Backend: Online     │ <- Status
│  Pages: 156          │
│  Status: Idle        │
├──────────────────────┤
│  Last: example.com   │
│  2 minutes ago       │
├──────────────────────┤
│ [Search] [Settings]  │ <- Actions
└──────────────────────┘
```

---

## 💡 Best Practices

### For Researchers
- Index papers and articles during research
- Use semantic search to find related content
- Export data before clearing browser

### For Developers
- Exclude localhost and dev domains
- Index documentation sites
- Search for code examples you've seen

### For General Browsing
- Let it run in background
- Search when you need to recall something
- Exclude sensitive sites (banking, etc.)

---

## 📞 Need More Help?

### Resources
- **Full Guide**: See `DEVELOPMENT_GUIDE.md`
- **Backend API**: http://localhost:8000/docs
- **Extension Details**: chrome://extensions → Details

### Quick Commands
```bash
# Check backend health
curl http://localhost:8000/health

# See indexed pages count
curl http://localhost:8000/stats

# Test search
curl "http://localhost:8000/search/keyword?q=test"
```

---

**Ready to go! Start browsing and building your personal web memory! 🚀**