# Installation Guide

## Quick Start (60 seconds)

```bash
# 1. Clone & setup
git clone https://github.com/ZaynJarvis/newtab
cd newtab

# 2. Get ARK API Token from bytedance ARK，then set it in env (or docker-compose.yml) file

# 3. Start backend (use simple config for local dev)
docker compose -f docker-compose.yml up -d

# 4. Load Chrome extension
# chrome://extensions/ → Developer mode → Load unpacked → Select 'extension' folder
```

## Prerequisites

- **Docker** ([Install](https://docs.docker.com/get-docker/)) or **Colima** (see below)
- **Chrome browser**
- **Git**

### Alternative: Colima (lightweight Docker for macOS)
```bash
brew install colima docker
colima start
```

## Setup Details

### Backend

```bash
# Start (2-5 min first time)
docker compose -f docker-compose.yml up -d

# Verify
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

### Chrome Extension

1. Chrome → `chrome://extensions/`
2. Developer mode ON
3. Load unpacked → Select `extension` folder
4. New tab → Custom interface appears

### Test Data

```bash
# Add page
curl -X POST "http://localhost:8000/index" \
  -H "Content-Type: application/json" \
  -d '{"url":"test.com","title":"Test","content":"test content"}'

# Search
curl "http://localhost:8000/search?q=test"
```

## Without Docker

```bash
cd backend && uv sync
uv run uvicorn src.main:app --reload
```

## Troubleshooting

**docker-compose not found**: Use `docker compose` (v2 syntax)

**Port 8000 in use**: `lsof -i :8000` → `kill -9 <PID>`

**No results**: Re-index test data (see Test Data section)

**Settings not saving**: Normal in file:// mode

## Commands

```bash
# Status
curl http://localhost:8000/health
docker compose -f docker-compose.yml ps

# Logs
docker compose -f docker-compose.yml logs

# Reset
docker compose -f docker-compose.yml down
rm -rf ./data ./logs
```

## Success Checklist

- [ ] Backend responds at http://localhost:8000/health
- [ ] Extension loaded in Chrome
- [ ] New tab shows custom interface
- [ ] Search returns results
- [ ] Settings panel opens

**Ready to use!** Visit [localhost:8000/docs](http://localhost:8000/docs) for API documentation.