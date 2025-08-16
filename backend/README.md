# Local Web Memory Backend

A FastAPI-powered service for local web page indexing and intelligent search with AI-generated keywords and vector embeddings.

## Quick Start

### 1. Set up Environment

```bash
cd backend

# Copy and configure environment file
cp .env.example .env
# Edit .env and set your ARK_API_TOKEN
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 3. Start the Server

```bash
# Simple command - all configuration from .env file
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server will start on http://localhost:8000 with:
- API documentation at http://localhost:8000/docs
- Health check at http://localhost:8000/health

## Configuration

### Environment Variables

Create a `.env` file from `.env.example` and configure:

```bash
# Required
ARK_API_TOKEN=your-ark-api-token-here

# Optional - Server Settings
HOST=0.0.0.0
PORT=8000
RELOAD=true
LOG_LEVEL=info

# Optional - API Configuration (use defaults unless custom)
# LLM_ENDPOINT=https://ark-cn-beijing.bytedance.net/api/v3/chat/completions
# EMBEDDING_ENDPOINT=https://ark-cn-beijing.bytedance.net/api/v3/embeddings/multimodal

# Optional - Performance Tuning
# MAX_RETRIES=3
# REQUEST_TIMEOUT=30.0
```

### Configuration Management

The backend uses `pydantic-settings` for configuration management:

- Environment variables take precedence
- `.env` file is loaded automatically
- Configuration is validated on startup
- All settings have sensible defaults (except ARK_API_TOKEN)

## API Endpoints

- `GET /` - Service information
- `GET /health` - Health check
- `POST /index` - Index a web page
- `GET /search?q=query` - Unified search
- `GET /pages` - List all pages
- `DELETE /pages/{id}` - Delete a page
- `GET /stats` - System statistics

## Development

### Mock Mode

If no ARK_API_TOKEN is provided, the service runs in mock mode for development:

```bash
# Unset ARK_API_TOKEN to use mock mode
unset ARK_API_TOKEN
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Health check
curl http://localhost:8000/health

# Search test
curl "http://localhost:8000/search?q=python"

# Index test
curl -X POST "http://localhost:8000/index" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "title": "Test", "content": "Test content"}'
```

## Features

- **Intelligent Search**: Combines keyword and semantic search
- **AI-Powered**: ByteDance ARK LLM for keywords and embeddings
- **Local Storage**: SQLite with FTS5 for fast full-text search
- **Vector Search**: High-dimensional semantic similarity
- **Query Caching**: LRU cache for embedding queries
- **ARC-based Frequency Tracking**: Smart page visit tracking
- **Auto-eviction**: Automatic cleanup of old/unused pages

## Architecture

- **FastAPI**: Modern async Python web framework
- **SQLite + FTS5**: Full-text search database
- **Vector Store**: In-memory vector similarity search
- **Pydantic Settings**: Type-safe configuration management
- **ByteDance ARK**: LLM and embedding API integration