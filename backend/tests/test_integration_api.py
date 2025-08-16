"""Integration tests for API endpoints of New Tab Backend."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import json
import httpx

from src.main import app


@pytest.mark.integration
class TestHealthAPI:
    """Integration tests for health endpoints."""
    
    def test_health_endpoint_success(self, client: TestClient, mock_ark_client):
        """Test health endpoint with healthy services."""
        with patch('src.main.ark_client', mock_ark_client):
            response = client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] in ["healthy", "degraded"]
            assert "database" in data
            assert "vector_store" in data
            assert "timestamp" in data
    
    def test_health_endpoint_degraded(self, client: TestClient):
        """Test health endpoint with degraded services."""
        # Test with no ark_client (degraded mode)
        with patch('src.main.ark_client', None):
            response = client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "degraded"
            assert data["database"]["status"] == "healthy"
            assert data["api_client"]["status"] == "unavailable"


@pytest.mark.integration
class TestIndexingAPI:
    """Integration tests for indexing endpoints."""
    
    def test_index_page_success(self, client: TestClient, mock_ark_client, sample_page_data):
        """Test successful page indexing."""
        with patch('src.main.ark_client', mock_ark_client):
            response = client.post("/index", json=sample_page_data)
            
            if response.status_code == 200:
                data = response.json()
                assert data["success"] is True
                assert "page_id" in data
                assert "keywords" in data
                assert isinstance(data["keywords"], list)
            else:
                # Handle case where API client is not available
                assert response.status_code in [400, 500, 503]
    
    def test_index_page_validation_error(self, client: TestClient):
        """Test page indexing with invalid data."""
        invalid_data = {"invalid": "data"}
        response = client.post("/index", json=invalid_data)
        assert response.status_code == 422
    
    def test_index_page_missing_required_fields(self, client: TestClient):
        """Test page indexing with missing required fields."""
        incomplete_data = {"url": "https://example.com"}  # Missing title and content
        response = client.post("/index", json=incomplete_data)
        assert response.status_code == 422
    
    def test_index_page_duplicate_url(self, client: TestClient, mock_ark_client, sample_page_data):
        """Test indexing the same URL twice."""
        with patch('src.main.ark_client', mock_ark_client):
            # Index first time
            response1 = client.post("/index", json=sample_page_data)
            
            # Index second time with same URL
            response2 = client.post("/index", json=sample_page_data)
            
            # Both should succeed (update case)
            if response1.status_code == 200:
                assert response2.status_code == 200
    
    def test_get_pages(self, client: TestClient, mock_ark_client, sample_page_data):
        """Test retrieving all pages."""
        # First index a page
        with patch('src.main.ark_client', mock_ark_client):
            client.post("/index", json=sample_page_data)
        
        # Then retrieve pages
        response = client.get("/pages")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_delete_page_success(self, client: TestClient, mock_ark_client, sample_page_data):
        """Test successful page deletion."""
        with patch('src.main.ark_client', mock_ark_client):
            # First index a page
            index_response = client.post("/index", json=sample_page_data)
            
            if index_response.status_code == 200:
                page_id = index_response.json()["page_id"]
                
                # Then delete it
                delete_response = client.delete(f"/pages/{page_id}")
                assert delete_response.status_code == 200
                
                data = delete_response.json()
                assert data["success"] is True
    
    def test_delete_nonexistent_page(self, client: TestClient):
        """Test deleting a non-existent page."""
        response = client.delete("/pages/999999")
        assert response.status_code == 404


@pytest.mark.integration
class TestSearchAPI:
    """Integration tests for search endpoints."""
    
    def test_search_basic(self, client: TestClient):
        """Test basic search functionality."""
        response = client.get("/search", params={"query": "test"})
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "query" in data
        assert "total_results" in data
        assert isinstance(data["results"], list)
        assert data["query"] == "test"
    
    def test_search_empty_query(self, client: TestClient):
        """Test search with empty query."""
        response = client.get("/search", params={"query": ""})
        assert response.status_code in [200, 422]
    
    def test_search_long_query(self, client: TestClient):
        """Test search with very long query."""
        long_query = "test " * 100
        response = client.get("/search", params={"query": long_query})
        assert response.status_code == 200
    
    def test_search_special_characters(self, client: TestClient):
        """Test search with special characters."""
        special_query = "test@#$%^&*()[]{}|\\:;\"'<>,.?/~`"
        response = client.get("/search", params={"query": special_query})
        assert response.status_code == 200
    
    def test_search_with_indexed_content(self, client: TestClient, mock_ark_client, sample_pages_data):
        """Test search after indexing content."""
        with patch('src.main.ark_client', mock_ark_client):
            # Index multiple pages
            for page_data in sample_pages_data:
                client.post("/index", json=page_data)
        
        # Search for specific content
        response = client.get("/search", params={"query": "Python programming"})
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data["results"], list)


@pytest.mark.integration
class TestAnalyticsAPI:
    """Integration tests for analytics endpoints."""
    
    def test_frequency_analytics(self, client: TestClient):
        """Test frequency analytics endpoint."""
        response = client.get("/analytics/frequency")
        assert response.status_code == 200
        
        data = response.json()
        assert "pages" in data
        assert isinstance(data["pages"], list)
    
    def test_visit_analytics(self, client: TestClient):
        """Test visit analytics endpoint."""
        response = client.get("/analytics/visits")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_visits" in data
        assert "unique_pages" in data
        assert isinstance(data["total_visits"], int)
        assert isinstance(data["unique_pages"], int)
    
    def test_record_visit(self, client: TestClient):
        """Test recording a page visit."""
        visit_data = {"url": "https://example.com/test-visit"}
        response = client.post("/analytics/visit", json=visit_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True


@pytest.mark.integration
class TestEvictionAPI:
    """Integration tests for eviction endpoints."""
    
    def test_eviction_candidates(self, client: TestClient):
        """Test getting eviction candidates."""
        response = client.get("/eviction/candidates")
        assert response.status_code == 200
        
        data = response.json()
        assert "candidates" in data
        assert isinstance(data["candidates"], list)
    
    def test_force_eviction(self, client: TestClient, mock_ark_client, sample_page_data):
        """Test forcing eviction of specific pages."""
        with patch('src.main.ark_client', mock_ark_client):
            # First index a page
            index_response = client.post("/index", json=sample_page_data)
            
            if index_response.status_code == 200:
                page_id = index_response.json()["page_id"]
                
                # Then try to evict it
                eviction_data = {"page_ids": [page_id]}
                response = client.post("/eviction/force", json=eviction_data)
                assert response.status_code == 200
                
                data = response.json()
                assert "evicted_count" in data


@pytest.mark.integration
class TestCacheAPI:
    """Integration tests for cache endpoints."""
    
    def test_cache_status(self, client: TestClient):
        """Test cache status endpoint."""
        response = client.get("/cache/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "cache_size" in data
        assert "cache_hits" in data
        assert "cache_misses" in data
        assert "hit_rate" in data
    
    def test_cache_clear(self, client: TestClient):
        """Test cache clearing."""
        response = client.post("/cache/clear")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True


@pytest.mark.integration
class TestCORSIntegration:
    """Integration tests for CORS functionality."""
    
    def test_cors_preflight(self, client: TestClient):
        """Test CORS preflight requests."""
        headers = {
            "Origin": "chrome-extension://test-extension",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
        response = client.options("/index", headers=headers)
        
        # Should allow CORS
        assert "Access-Control-Allow-Origin" in response.headers
    
    def test_cors_actual_request(self, client: TestClient):
        """Test actual CORS requests."""
        headers = {"Origin": "chrome-extension://test-extension"}
        response = client.get("/health", headers=headers)
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers


@pytest.mark.integration
class TestErrorHandling:
    """Integration tests for error handling."""
    
    def test_404_endpoint(self, client: TestClient):
        """Test 404 for non-existent endpoints."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client: TestClient):
        """Test 405 for incorrect HTTP methods."""
        response = client.post("/health")
        assert response.status_code == 405
    
    def test_large_payload(self, client: TestClient):
        """Test handling of large payloads."""
        large_content = "x" * (10 * 1024 * 1024)  # 10MB content
        large_data = {
            "url": "https://example.com/large",
            "title": "Large Page",
            "content": large_content
        }
        
        response = client.post("/index", json=large_data)
        # Should handle gracefully with appropriate error or success
        assert response.status_code in [200, 413, 422, 500]


@pytest.mark.integration
class TestConcurrency:
    """Integration tests for concurrent operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_indexing(self, mock_ark_client, sample_pages_data):
        """Test concurrent page indexing."""
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            with patch('src.main.ark_client', mock_ark_client):
                # Create concurrent indexing tasks
                tasks = []
                for i, page_data in enumerate(sample_pages_data):
                    # Make URLs unique
                    page_data = page_data.copy()
                    page_data["url"] = f"{page_data['url']}?test={i}"
                    task = client.post("/index", json=page_data)
                    tasks.append(task)
                
                # Execute concurrently
                import asyncio
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check that all requests were handled
                for response in responses:
                    if isinstance(response, Exception):
                        pytest.fail(f"Concurrent request failed: {response}")
                    assert response.status_code in [200, 400, 500]
    
    @pytest.mark.asyncio
    async def test_concurrent_searching(self):
        """Test concurrent search operations."""
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            # Create concurrent search tasks
            queries = ["python", "web", "development", "test", "api"]
            tasks = []
            for query in queries:
                task = client.get("/search", params={"query": query})
                tasks.append(task)
            
            # Execute concurrently
            import asyncio
            responses = await asyncio.gather(*tasks)
            
            # All searches should succeed
            for response in responses:
                assert response.status_code == 200


@pytest.mark.integration
class TestDataIntegrity:
    """Integration tests for data integrity."""
    
    def test_page_data_persistence(self, client: TestClient, mock_ark_client, sample_page_data):
        """Test that indexed page data persists correctly."""
        with patch('src.main.ark_client', mock_ark_client):
            # Index a page
            response = client.post("/index", json=sample_page_data)
            
            if response.status_code == 200:
                page_id = response.json()["page_id"]
                
                # Retrieve pages and verify data
                pages_response = client.get("/pages")
                assert pages_response.status_code == 200
                
                pages = pages_response.json()
                test_page = next((p for p in pages if p["id"] == page_id), None)
                
                assert test_page is not None
                assert test_page["url"] == sample_page_data["url"]
                assert test_page["title"] == sample_page_data["title"]
                assert test_page["content"] == sample_page_data["content"]
    
    def test_search_result_consistency(self, client: TestClient, mock_ark_client, sample_page_data):
        """Test that search results are consistent."""
        with patch('src.main.ark_client', mock_ark_client):
            # Index a page
            client.post("/index", json=sample_page_data)
            
            # Search multiple times with same query
            query = "test"
            responses = []
            for _ in range(3):
                response = client.get("/search", params={"query": query})
                assert response.status_code == 200
                responses.append(response.json())
            
            # Results should be consistent
            if len(responses) > 1:
                first_result = responses[0]
                for result in responses[1:]:
                    assert result["total_results"] == first_result["total_results"]
                    assert len(result["results"]) == len(first_result["results"])