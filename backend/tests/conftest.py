"""Pytest configuration and fixtures for New Tab Backend tests."""

import asyncio
import os
import tempfile
import shutil
from typing import Generator, AsyncGenerator
import pytest
import httpx
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

# Set test environment variables before importing the app
os.environ["API_TOKEN"] = "test-token-for-testing"
os.environ["LLM_PROVIDER"] = "openai"  # Use OpenAI for tests
os.environ["EMBEDDING_PROVIDER"] = "openai"
os.environ["DATABASE_FILE"] = ":memory:"
os.environ["QUERY_CACHE_FILE"] = "/tmp/test_query_cache.json"
os.environ["LOG_LEVEL"] = "error"  # Reduce noise in tests

from src.main import app, db, vector_store, ark_client
from src.core.database import Database
from src.services.vector_store import VectorStore
from src.services.multi_provider_client import MultiProviderAPIClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_db() -> Generator[Database, None, None]:
    """Create a test database instance."""
    test_db = Database(":memory:")
    yield test_db
    # No cleanup needed for in-memory database


@pytest.fixture
def test_vector_store() -> Generator[VectorStore, None, None]:
    """Create a test vector store instance."""
    test_vs = VectorStore(dimension=2048)
    yield test_vs
    # Vector store uses in-memory storage, no cleanup needed


@pytest.fixture
def mock_ark_client() -> Generator[MagicMock, None, None]:
    """Create a mock multi-provider API client."""
    mock_client = MagicMock(spec=MultiProviderAPIClient)
    
    # Mock common methods
    mock_client.health_check = AsyncMock(return_value={
        "status": "healthy",
        "llm_provider": {"provider_type": "OpenAIProvider", "status": "healthy"},
        "embedding_provider": {"provider_type": "OpenAIProvider", "status": "available"}
    })
    mock_client.generate_keywords_and_description = AsyncMock(return_value={
        "keywords": "test, keyword, sample",
        "description": "Test description",
        "improved_title": "Test Title"
    })
    mock_client.generate_embedding = AsyncMock(return_value=[0.1] * 3072)  # OpenAI embedding dimension
    mock_client.get_cache_stats = MagicMock(return_value={
        "size": 0,
        "hits": 0,
        "misses": 0,
        "hit_rate": 0.0
    })
    mock_client.clear_cache = MagicMock(return_value=True)
    mock_client.cleanup_cache = MagicMock(return_value=0)
    mock_client.get_top_cached_queries = MagicMock(return_value=[])
    
    # Mock query cache
    mock_client.query_cache = MagicMock()
    mock_client.query_cache.force_save = MagicMock(return_value=True)
    
    yield mock_client


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_page_data() -> dict:
    """Sample page data for testing."""
    return {
        "url": "https://example.com/test-page",
        "title": "Test Page Title",
        "content": "This is test content for a web page with some keywords.",
        "metadata": {
            "author": "Test Author",
            "description": "Test page description",
            "keywords": "test, web, page"
        }
    }


@pytest.fixture
def sample_pages_data() -> list[dict]:
    """Sample multiple pages data for testing."""
    return [
        {
            "url": "https://example.com/page1",
            "title": "First Test Page",
            "content": "Content about Python programming and web development.",
            "metadata": {"author": "Author 1", "tags": "python,web"}
        },
        {
            "url": "https://example.com/page2",
            "title": "Second Test Page",
            "content": "Content about machine learning and data science.",
            "metadata": {"author": "Author 2", "tags": "ml,data"}
        },
        {
            "url": "https://example.com/page3",
            "title": "Third Test Page",
            "content": "Content about FastAPI and backend development.",
            "metadata": {"author": "Author 3", "tags": "fastapi,backend"}
        }
    ]


@pytest.fixture
def playwright_config() -> dict:
    """Playwright configuration for E2E tests."""
    return {
        "headless": True,
        "browser_type": "chromium",
        "viewport": {"width": 1280, "height": 720},
        "timeout": 30000,
        "base_url": "http://localhost:8000"
    }


# Pytest markers for different test categories
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance benchmark tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


@pytest.fixture(autouse=True)
def reset_app_state():
    """Reset application state before each test."""
    # Clear vector store
    if hasattr(vector_store, '_vectors'):
        vector_store._vectors.clear()
    if hasattr(vector_store, '_metadata'):
        vector_store._metadata.clear()
    
    # Reset database for tests that use the global db instance
    if hasattr(db, 'connection'):
        # For in-memory database, we can recreate tables
        try:
            db.init_tables()
        except Exception:
            pass  # Tables might already exist
    
    yield
    
    # Cleanup after test if needed
    pass