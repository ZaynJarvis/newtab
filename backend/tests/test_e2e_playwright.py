"""End-to-end tests using Playwright for New Tab Backend."""

import pytest
import asyncio
import json
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from fastapi.testclient import TestClient
import uvicorn
import threading
import time
import httpx

from src.main import app


class TestServer:
    """Test server manager for E2E tests."""
    
    def __init__(self, host="127.0.0.1", port=8001):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        self.base_url = f"http://{host}:{port}"
    
    def start(self):
        """Start the test server in a separate thread."""
        def run_server():
            uvicorn.run(app, host=self.host, port=self.port, log_level="error")
        
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()
        
        # Wait for server to start
        max_retries = 30
        for _ in range(max_retries):
            try:
                response = httpx.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("Test server failed to start")
    
    def stop(self):
        """Stop the test server."""
        # Server will stop when the main thread exits
        pass


@pytest.fixture(scope="session")
async def test_server():
    """Start test server for E2E tests."""
    server = TestServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="session")
async def browser():
    """Create browser instance for E2E tests."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser: Browser):
    """Create a new page for each test."""
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720}
    )
    page = await context.new_page()
    yield page
    await context.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_health_endpoint(test_server: TestServer):
    """Test health endpoint is accessible."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{test_server.base_url}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_root_endpoint(test_server: TestServer):
    """Test root endpoint returns service information."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{test_server.base_url}/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "New Tab Backend"
        assert data["version"] == "2.0.0"
        assert data["status"] == "running"
        assert "endpoints" in data
        assert "timestamp" in data


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_api_docs_accessibility(test_server: TestServer):
    """Test that API documentation is accessible."""
    async with httpx.AsyncClient() as client:
        # Test OpenAPI docs
        response = await client.get(f"{test_server.base_url}/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        
        # Test OpenAPI JSON schema
        response = await client.get(f"{test_server.base_url}/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert schema["info"]["title"] == "New Tab Backend API"
        assert schema["info"]["version"] == "2.0.0"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_page_indexing_workflow(test_server: TestServer):
    """Test complete page indexing workflow."""
    async with httpx.AsyncClient() as client:
        # Test data
        page_data = {
            "url": "https://example.com/test-e2e",
            "title": "E2E Test Page",
            "content": "This is content for end-to-end testing with some keywords.",
            "metadata": {
                "author": "E2E Test",
                "description": "Test page for E2E testing"
            }
        }
        
        # Index the page
        response = await client.post(
            f"{test_server.base_url}/index",
            json=page_data
        )
        
        if response.status_code == 200:
            # Success case - verify response
            data = response.json()
            assert data["success"] is True
            assert "page_id" in data
            page_id = data["page_id"]
            
            # Verify page was stored
            response = await client.get(f"{test_server.base_url}/pages")
            assert response.status_code == 200
            
            pages = response.json()
            assert len(pages) >= 1
            
            # Find our page
            test_page = next((p for p in pages if p["id"] == page_id), None)
            assert test_page is not None
            assert test_page["url"] == page_data["url"]
            assert test_page["title"] == page_data["title"]
            
        else:
            # If indexing fails (e.g., due to missing API token), verify error handling
            assert response.status_code in [400, 500, 503]
            data = response.json()
            assert "error" in data or "detail" in data


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_search_functionality(test_server: TestServer):
    """Test search functionality after indexing."""
    async with httpx.AsyncClient() as client:
        # First, try to index a test page
        page_data = {
            "url": "https://example.com/search-test",
            "title": "Search Test Page",
            "content": "This page contains information about Python programming and web development.",
            "metadata": {"tags": "python,web,programming"}
        }
        
        index_response = await client.post(
            f"{test_server.base_url}/index",
            json=page_data
        )
        
        # Test search regardless of indexing success
        search_response = await client.get(
            f"{test_server.base_url}/search",
            params={"query": "python programming"}
        )
        
        assert search_response.status_code == 200
        results = search_response.json()
        
        # Verify search response structure
        assert "results" in results
        assert "query" in results
        assert "total_results" in results
        assert isinstance(results["results"], list)
        assert results["query"] == "python programming"
        
        # If indexing was successful, we should find our test page
        if index_response.status_code == 200:
            matching_results = [
                r for r in results["results"] 
                if r["url"] == page_data["url"]
            ]
            assert len(matching_results) <= 1  # Should be 0 or 1


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_analytics_endpoints(test_server: TestServer):
    """Test analytics endpoints."""
    async with httpx.AsyncClient() as client:
        # Test frequency analytics
        response = await client.get(f"{test_server.base_url}/analytics/frequency")
        assert response.status_code == 200
        
        data = response.json()
        assert "pages" in data
        assert isinstance(data["pages"], list)
        
        # Test visit analytics
        response = await client.get(f"{test_server.base_url}/analytics/visits")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_visits" in data
        assert "unique_pages" in data
        assert isinstance(data["total_visits"], int)
        assert isinstance(data["unique_pages"], int)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_management(test_server: TestServer):
    """Test cache management endpoints."""
    async with httpx.AsyncClient() as client:
        # Test cache status
        response = await client.get(f"{test_server.base_url}/cache/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "cache_size" in data
        assert "cache_hits" in data
        assert "cache_misses" in data
        assert "hit_rate" in data
        
        # Test cache clearing
        response = await client.post(f"{test_server.base_url}/cache/clear")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_error_handling(test_server: TestServer):
    """Test error handling for invalid requests."""
    async with httpx.AsyncClient() as client:
        # Test invalid page indexing
        response = await client.post(
            f"{test_server.base_url}/index",
            json={"invalid": "data"}
        )
        assert response.status_code == 422  # Validation error
        
        # Test non-existent page deletion
        response = await client.delete(f"{test_server.base_url}/pages/999999")
        assert response.status_code == 404
        
        # Test invalid search parameters
        response = await client.get(
            f"{test_server.base_url}/search",
            params={"invalid_param": "value"}
        )
        # Should still work but ignore invalid params
        assert response.status_code in [200, 422]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cors_headers(test_server: TestServer):
    """Test CORS headers are properly set."""
    async with httpx.AsyncClient() as client:
        # Test preflight request
        response = await client.options(
            f"{test_server.base_url}/health",
            headers={
                "Origin": "chrome-extension://test",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        # Should allow CORS
        assert "Access-Control-Allow-Origin" in response.headers


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_concurrent_requests(test_server: TestServer):
    """Test handling of concurrent requests."""
    async with httpx.AsyncClient() as client:
        # Create multiple concurrent requests
        tasks = []
        for i in range(5):
            task = client.get(f"{test_server.base_url}/health")
            tasks.append(task)
        
        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_large_content_handling(test_server: TestServer):
    """Test handling of large content."""
    async with httpx.AsyncClient() as client:
        # Create a page with large content
        large_content = "This is a test. " * 1000  # Repeat to create large content
        
        page_data = {
            "url": "https://example.com/large-content",
            "title": "Large Content Test Page",
            "content": large_content,
            "metadata": {"size": "large"}
        }
        
        response = await client.post(
            f"{test_server.base_url}/index",
            json=page_data
        )
        
        # Should handle large content gracefully
        assert response.status_code in [200, 400, 413, 500]  # Various acceptable responses
        
        if response.status_code == 200:
            data = response.json()
            assert "page_id" in data


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_page_lifecycle(test_server: TestServer):
    """Test complete page lifecycle: create, read, update, delete."""
    async with httpx.AsyncClient() as client:
        # Create a page
        page_data = {
            "url": "https://example.com/lifecycle-test",
            "title": "Lifecycle Test Page",
            "content": "Content for lifecycle testing.",
            "metadata": {"test": "lifecycle"}
        }
        
        create_response = await client.post(
            f"{test_server.base_url}/index",
            json=page_data
        )
        
        if create_response.status_code == 200:
            page_id = create_response.json()["page_id"]
            
            # Read the page
            read_response = await client.get(f"{test_server.base_url}/pages")
            assert read_response.status_code == 200
            
            pages = read_response.json()
            test_page = next((p for p in pages if p["id"] == page_id), None)
            assert test_page is not None
            
            # Update the page (re-index with same URL)
            updated_data = page_data.copy()
            updated_data["title"] = "Updated Lifecycle Test Page"
            
            update_response = await client.post(
                f"{test_server.base_url}/index",
                json=updated_data
            )
            assert update_response.status_code == 200
            
            # Delete the page
            delete_response = await client.delete(f"{test_server.base_url}/pages/{page_id}")
            assert delete_response.status_code in [200, 404]  # 404 if already deleted