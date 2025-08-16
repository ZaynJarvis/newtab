# Development Guide

## Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management

### Setup
1. Clone the repository
2. Navigate to the backend directory
3. Set your ARK API token:
   ```bash
   export ARK_API_TOKEN="your-token-here"
   ```
4. Start the server:
   ```bash
   ./scripts/start_server.sh
   ```

### Development Scripts

All scripts are located in the `scripts/` directory:

#### `start_server.sh`
Starts the development server with automatic dependency installation.

```bash
./scripts/start_server.sh
```

Features:
- Automatically installs/updates dependencies using uv
- Checks for required environment variables
- Provides helpful startup information

#### `run_tests.sh`
Runs the test suite with various options.

```bash
./scripts/run_tests.sh [cache|unit|coverage|verbose|all]
```

Options:
- `cache` - Run only cache tests
- `unit` - Run unit tests with short traceback
- `coverage` - Run tests with coverage analysis
- `verbose` - Run tests with verbose output
- `all` - Run all tests (default)

#### `seed_data.py`
Seeds the database with sample data for testing.

```bash
uv run python scripts/seed_data.py
```

Features:
- Creates sample web pages
- Generates AI keywords and descriptions (if API token is available)
- Creates vector embeddings
- Provides test data for development

## Project Structure

```
backend/
├── src/                    # Source code
│   ├── api/               # API route handlers
│   ├── core/              # Core business logic
│   ├── services/          # External service integrations
│   ├── cache/             # Caching implementations
│   └── main.py           # Application entry point
├── tests/                 # Test files
├── scripts/               # Development scripts
├── docs/                  # Documentation
└── arc/                   # ARC eviction policy
```

## API Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /stats` - System statistics
- `GET /` - Service information

### Page Management
- `POST /index` - Index a new page
- `GET /pages` - List pages with pagination
- `GET /pages/{id}` - Get specific page
- `DELETE /pages/{id}` - Delete page

### Search
- `GET /search?q=query` - Unified search

### Analytics
- `POST /track-visit` - Track page visit
- `GET /analytics/frequency` - Get visit analytics

### Eviction Management
- `POST /eviction/run` - Manually trigger eviction
- `GET /eviction/preview` - Preview eviction candidates
- `GET /eviction/stats` - Get eviction statistics

### Cache Management
- `GET /cache/query/stats` - Cache statistics
- `GET /cache/query/top` - Top cached queries
- `POST /cache/query/clear` - Clear cache
- `POST /cache/query/cleanup` - Clean expired entries

## Configuration

Configuration is managed through `src/core/config.py` using Pydantic Settings.

### Environment Variables
Create a `.env` file in the backend directory:

```env
ARK_API_TOKEN=your-api-token-here
HOST=0.0.0.0
PORT=8000
RELOAD=true
LOG_LEVEL=info
```

### Configuration Options
- **API Settings**: Endpoints, models, timeouts, retries
- **Server Settings**: Host, port, reload, logging
- **Cache Settings**: Capacity, TTL, file location
- **Vector Settings**: Dimension, similarity thresholds

## Testing

### Running Tests
```bash
# All tests
./scripts/run_tests.sh

# With coverage
./scripts/run_tests.sh coverage

# Specific test file
uv run python -m pytest tests/test_query_cache.py -v
```

### Test Structure
- `tests/test_query_cache.py` - Query embedding cache tests
- Add new test files in the `tests/` directory
- Follow the naming convention `test_*.py`

### Writing Tests
```python
import unittest
from src.cache.query_embedding_cache import QueryEmbeddingCache

class TestMyFeature(unittest.TestCase):
    def test_something(self):
        # Your test code here
        pass
```

## Database

### Schema
The database uses SQLite with FTS5 extension:
- `pages` - Main content table
- `pages_fts` - Full-text search virtual table

### Migrations
Migrations are handled automatically in `database.py`:
- New columns are added via `_migrate_add_frequency_fields()`
- Database initialization creates all required tables

### Manual Database Operations
```python
from src.core.database import Database

db = Database()
pages = db.get_all_pages(limit=10)
total = db.get_total_pages()
```

## API Client

### ByteDance ARK Integration
The API client handles:
- LLM requests for keyword generation
- Embedding generation for semantic search
- Automatic retries with exponential backoff
- Query result caching

### Mock Mode
If `ARK_API_TOKEN` is not set, the system runs in mock mode:
- Uses generated mock embeddings
- Skips LLM-based keyword generation
- All functionality remains available for testing

## Vector Search

### Implementation
- In-memory vector store using NumPy
- Cosine similarity with normalized vectors
- Advanced filtering with clustering analysis
- Similarity drop detection for result quality

### Adding Vectors
```python
from src.services.vector_store import VectorStore

store = VectorStore(dimension=2048)
store.add_vector(page_id, embedding_vector, page_data)
results = store.search(query_vector, limit=10)
```

## Error Handling

### API Errors
All endpoints use structured error responses:
```json
{
    "detail": "Error description"
}
```

### Logging
Configure logging level via `LOG_LEVEL` environment variable:
- `debug` - Detailed debugging information
- `info` - General information (default)
- `warning` - Warning messages
- `error` - Error messages only

## Performance

### Optimization Tips
- Vector store is in-memory for fast search
- Query embeddings are cached with LRU policy
- Database uses indexes on frequently queried columns
- Background tasks handle expensive AI processing

### Monitoring
- Check `/health` endpoint for system status
- Monitor `/stats` for database and vector store metrics
- Use `/cache/query/stats` for cache performance

## Debugging

### Common Issues
1. **Import Errors**: Ensure you're using `uv run` for all Python commands
2. **API Token**: Set `ARK_API_TOKEN` environment variable
3. **Dependencies**: Run `uv sync` to update dependencies
4. **Database**: Check `web_memory.db` file permissions

### Development Tools
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health