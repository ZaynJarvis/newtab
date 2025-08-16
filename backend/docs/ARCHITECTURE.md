# Local Web Memory Backend - Architecture

## Project Structure

```
backend/
├── src/                    # Core application code
│   ├── api/               # API endpoints (FastAPI routers)
│   │   ├── __init__.py
│   │   ├── health.py      # Health check and system stats
│   │   ├── indexing.py    # Page indexing and management
│   │   ├── search.py      # Unified search endpoints
│   │   ├── analytics.py   # Visit tracking and analytics
│   │   ├── eviction.py    # Page eviction management
│   │   └── cache.py       # Query cache management
│   ├── core/              # Core business logic
│   │   ├── __init__.py
│   │   ├── config.py      # Application configuration
│   │   ├── database.py    # SQLite database operations
│   │   └── models.py      # Pydantic data models
│   ├── services/          # External services
│   │   ├── __init__.py
│   │   ├── api_client.py  # ByteDance ARK API client
│   │   └── vector_store.py # In-memory vector storage
│   ├── cache/             # Caching implementations
│   │   ├── __init__.py
│   │   └── query_embedding_cache.py # LRU cache for embeddings
│   ├── __init__.py
│   └── main.py           # Main application entry point
├── tests/                 # All test files
│   ├── __init__.py
│   └── test_query_cache.py
├── scripts/               # Utility scripts
│   ├── start_server.sh    # Server startup script
│   ├── run_tests.sh       # Test runner script
│   └── seed_data.py       # Database seeding script
├── docs/                  # Backend documentation
│   └── ARCHITECTURE.md    # This file
├── arc/                   # ARC eviction policy (existing)
│   ├── __init__.py
│   ├── arc_cache.py
│   ├── eviction.py
│   └── utils.py
├── pyproject.toml         # Python project configuration
├── uv.lock               # Dependency lock file
└── README.md             # Main documentation
```

## Architecture Overview

### 1. API Layer (`src/api/`)

The API layer is split into focused modules using FastAPI routers:

- **health.py** - Health checks and system statistics
- **indexing.py** - Page indexing, retrieval, and deletion
- **search.py** - Unified keyword and semantic search
- **analytics.py** - Visit tracking and frequency analytics
- **eviction.py** - Page eviction and memory management
- **cache.py** - Query embedding cache management

Each API module uses dependency injection to access shared services.

### 2. Core Layer (`src/core/`)

Contains the core business logic and data models:

- **config.py** - Centralized configuration using Pydantic Settings
- **database.py** - SQLite database operations with FTS5 support
- **models.py** - Pydantic models for request/response validation

### 3. Services Layer (`src/services/`)

External service integrations:

- **api_client.py** - ByteDance ARK API client for LLM and embeddings
- **vector_store.py** - In-memory vector storage with similarity search

### 4. Cache Layer (`src/cache/`)

Caching implementations:

- **query_embedding_cache.py** - LRU cache for query embeddings with disk persistence

## Key Features

### Configuration Management
- Uses Pydantic Settings for type-safe configuration
- Environment variable support with `.env` file loading
- Validation and sensible defaults

### Database Layer
- SQLite with FTS5 for full-text search
- Vector embedding storage as JSON
- Automatic schema migrations
- ARC-based page eviction for memory management

### Search System
- Parallel execution of keyword and semantic search
- Server-controlled result mixing (70% semantic, 30% keyword)
- Advanced filtering with similarity drop detection
- Frequency-based result boosting

### Caching
- LRU cache for query embeddings
- Automatic disk persistence
- TTL-based expiration
- Thread-safe operations

### API Design
- RESTful endpoints with OpenAPI documentation
- Structured error handling
- Background task processing
- CORS support for browser extensions

## Development Workflow

### Starting the Server
```bash
# Using the provided script
./scripts/start_server.sh

# Or manually with uv
uv run python -m src.main
```

### Running Tests
```bash
# Using the provided script
./scripts/run_tests.sh

# Different test modes
./scripts/run_tests.sh cache     # Cache tests only
./scripts/run_tests.sh coverage  # With coverage report
./scripts/run_tests.sh verbose   # Verbose output
```

### Seeding Data
```bash
# Add sample data for testing
uv run python scripts/seed_data.py
```

## Dependencies

- **FastAPI** - Modern async web framework
- **Pydantic** - Data validation and settings
- **SQLite** - Database with FTS5 extension
- **NumPy** - Vector operations
- **scikit-learn** - ML clustering for search
- **httpx** - Async HTTP client
- **pytest** - Testing framework

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ARK_API_TOKEN` | ByteDance ARK API token | Required |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `RELOAD` | Enable auto-reload | `true` |
| `LOG_LEVEL` | Logging level | `info` |

## API Documentation

When the server is running, visit:
- **OpenAPI Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health