# New Tab - Master Implementation Plan

## Project Overview
Build a privacy-first Chrome extension that automatically indexes visited web pages locally, generates keywords/descriptions via LLM, and provides instant semantic search from a new tab interface.

## Parallel Execution Strategy

### Track A: Backend + AI Integration
**Phase 1A: Backend Foundation**
- FastAPI with Python 3.11+, SQLite FTS5 for keyword search
- Simple in-memory vector store (upgrade to Qdrant later)
- REST API endpoints: /index, /search/keyword, /search/vector, /pages CRUD
- Mock data generator for testing

**Phase 4A: AI Integration** (starts after 1A)
- ByteDance Ark API integration (LLM + embeddings)
- Real keyword/description generation
- Real vector embeddings
- Error handling and retries

### Track B: Extension + UI
**Phase 2B: Chrome Extension Core**
- Manifest V3 setup with minimal permissions
- Content script for DOM extraction
- Service worker for background processing
- Communication with localhost backend

**Phase 3B: Search Interface** (starts after 2B)
- New tab override with search UI
- Real-time search components
- Result cards with actions
- Settings panel for privacy controls

## Key Requirements

### Backend (Track A)
- FastAPI service on localhost:8000
- SQLite database with FTS5 virtual table for keyword search
- Vector storage for semantic search (in-memory → Qdrant)
- Response times: <100ms API, <500ms search
- Support 1000+ documents

### Extension (Track B)
- Chrome Extension Manifest V3
- Content extraction from any webpage
- Service worker handles indexing pipeline
- New tab override with instant search
- Privacy-first design (local storage only)

### External APIs (ByteDance Ark)
```bash
# API Token
export ARK_API_TOKEN="16997291-4771-4dc9-9a42-4acc930897fa"

# LLM API for keywords/descriptions
curl https://ark-cn-beijing.bytedance.net/api/v3/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_TOKEN" \
  -d '{
    "model": "ep-20250529215531-dfpgt",
    "messages": [{"role": "user", "content": "Generate keywords for: [page content]"}]
  }'

# Embedding API for vectors
curl https://ark-cn-beijing.bytedance.net/api/v3/embeddings/multimodal \
   -H "Content-Type: application/json" \
   -H "Authorization: Bearer $ARK_API_TOKEN" \
   -d '{
    "model": "ep-20250529220411-grkkv",
    "input": [{"type":"text", "text":"[page content]"}]
  }'
```

## Data Model
```python
# Page Entry
{
    "id": int,
    "url": str,  # Full URL including query params
    "title": str,
    "description": str,
    "keywords": str,
    "content": str,  # Extracted main content
    "favicon_url": str,
    "created_at": datetime,
    "vector_embedding": List[float]  # 1536 dimensions
}
```

## Project Structure
```
newtab/
├── docs/
│   ├── phase-plans/
│   └── demo-scripts/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── models.py            # Data models
│   ├── database.py          # SQLite + FTS5
│   ├── vector_store.py      # Vector operations
│   ├── api_client.py        # Ark API integration
│   └── requirements.txt
├── extension/
│   ├── manifest.json        # MV3 manifest
│   ├── background/
│   │   └── service-worker.js
│   ├── content/
│   │   └── content-script.js
│   ├── newtab/
│   │   ├── index.html
│   │   ├── app.js
│   │   └── styles.css
│   └── popup/
└── demo/
    └── test-data-generator.py
```

## Success Criteria
- **Demo 1** (1A + 2B): Backend API working + Extension indexing real pages
- **Demo 2** (All phases): Full search experience with AI-powered relevance
- Performance: <500ms search, <2s indexing per page
- Privacy: All data local, user controls for exclusions

## Git Strategy
- Feature branches for each track
- Regular commits with working increments
- Tags for demo milestones
- Main branch always deployable

## Technical Stack Summary
- **Backend**: FastAPI, SQLite FTS5, in-memory vectors → Qdrant
- **Extension**: Vanilla JS, Web Components, Chrome APIs
- **AI**: ByteDance Ark API for LLM + embeddings
- **Database**: SQLite with FTS5 virtual tables
- **Deployment**: Local development, Docker for backend