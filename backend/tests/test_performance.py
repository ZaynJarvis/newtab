"""Performance benchmark tests for New Tab Backend."""

import pytest
import time
import asyncio
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import psutil
import os

from src.main import app


@pytest.fixture
def performance_client():
    """Create a test client optimized for performance testing."""
    return TestClient(app)


@pytest.fixture
def mock_fast_ark_client():
    """Create a fast mock ARK client for performance testing."""
    mock_client = MagicMock()
    mock_client.health_check = AsyncMock(return_value={"status": "healthy"})
    mock_client.generate_keywords = AsyncMock(return_value=["test", "keyword", "fast"])
    mock_client.get_embeddings = AsyncMock(return_value=[0.1] * 2048)
    mock_client.get_cache_stats = MagicMock(return_value={
        "size": 100,
        "hits": 80,
        "misses": 20,
        "hit_rate": 0.8
    })
    mock_client.query_cache = MagicMock()
    mock_client.query_cache.force_save = MagicMock(return_value=True)
    return mock_client


@pytest.fixture
def sample_pages_bulk():
    """Generate bulk sample pages for performance testing."""
    pages = []
    for i in range(100):
        pages.append({
            "url": f"https://example.com/perf-test-{i}",
            "title": f"Performance Test Page {i}",
            "content": f"This is performance test content for page {i}. " * 10,
            "metadata": {
                "author": f"Author {i}",
                "category": f"category_{i % 5}",
                "tags": f"tag{i % 3},performance,test"
            }
        })
    return pages


class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.duration = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time


@pytest.mark.performance
class TestAPIPerformance:
    """Performance tests for API endpoints."""
    
    def test_health_endpoint_latency(self, performance_client):
        """Test health endpoint response time."""
        times = []
        for _ in range(10):
            with PerformanceTimer() as timer:
                response = performance_client.get("/health")
                assert response.status_code == 200
            times.append(timer.duration)
        
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        # Health endpoint should be very fast
        assert avg_time < 0.1, f"Average response time {avg_time:.3f}s exceeds 100ms"
        assert max_time < 0.5, f"Max response time {max_time:.3f}s exceeds 500ms"
        
        print(f"Health endpoint - Avg: {avg_time:.3f}s, Max: {max_time:.3f}s")
    
    def test_search_endpoint_latency(self, performance_client):
        """Test search endpoint response time."""
        search_queries = [
            "python programming",
            "web development",
            "machine learning",
            "data science",
            "artificial intelligence"
        ]
        
        times = []
        for query in search_queries:
            with PerformanceTimer() as timer:
                response = performance_client.get("/search", params={"query": query})
                assert response.status_code == 200
            times.append(timer.duration)
        
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        # Search should be reasonably fast
        assert avg_time < 2.0, f"Average search time {avg_time:.3f}s exceeds 2s"
        assert max_time < 5.0, f"Max search time {max_time:.3f}s exceeds 5s"
        
        print(f"Search endpoint - Avg: {avg_time:.3f}s, Max: {max_time:.3f}s")
    
    def test_index_endpoint_latency(self, performance_client, mock_fast_ark_client):
        """Test indexing endpoint response time."""
        with patch('src.main.ark_client', mock_fast_ark_client):
            sample_pages = [
                {
                    "url": f"https://example.com/perf-{i}",
                    "title": f"Performance Test {i}",
                    "content": f"Test content for performance page {i}",
                    "metadata": {"test": f"perf_{i}"}
                }
                for i in range(5)
            ]
            
            times = []
            for page in sample_pages:
                with PerformanceTimer() as timer:
                    response = performance_client.post("/index", json=page)
                    assert response.status_code in [200, 400, 500]
                times.append(timer.duration)
            
            avg_time = statistics.mean(times)
            max_time = max(times)
            
            # Indexing can take longer but should be reasonable
            assert avg_time < 5.0, f"Average indexing time {avg_time:.3f}s exceeds 5s"
            assert max_time < 10.0, f"Max indexing time {max_time:.3f}s exceeds 10s"
            
            print(f"Index endpoint - Avg: {avg_time:.3f}s, Max: {max_time:.3f}s")


@pytest.mark.performance
class TestConcurrencyPerformance:
    """Performance tests for concurrent operations."""
    
    def test_concurrent_health_checks(self, performance_client):
        """Test performance under concurrent health check load."""
        num_requests = 50
        
        def make_request():
            with PerformanceTimer() as timer:
                response = performance_client.get("/health")
                return response.status_code, timer.duration
        
        # Execute concurrent requests
        with PerformanceTimer() as total_timer:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(num_requests)]
                results = [future.result() for future in as_completed(futures)]
        
        # Analyze results
        status_codes = [result[0] for result in results]
        times = [result[1] for result in results]
        
        success_rate = sum(1 for code in status_codes if code == 200) / len(status_codes)
        avg_time = statistics.mean(times)
        total_time = total_timer.duration
        throughput = num_requests / total_time
        
        # Assertions
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95%"
        assert avg_time < 1.0, f"Average response time {avg_time:.3f}s exceeds 1s"
        assert throughput > 10, f"Throughput {throughput:.1f} req/s below 10 req/s"
        
        print(f"Concurrent health checks - Success: {success_rate:.2%}, "
              f"Avg time: {avg_time:.3f}s, Throughput: {throughput:.1f} req/s")
    
    def test_concurrent_searches(self, performance_client):
        """Test performance under concurrent search load."""
        queries = [
            "python", "javascript", "machine learning", "web development",
            "data science", "artificial intelligence", "backend", "frontend",
            "database", "api"
        ]
        
        def make_search(query):
            with PerformanceTimer() as timer:
                response = performance_client.get("/search", params={"query": query})
                return response.status_code, timer.duration
        
        # Execute concurrent searches
        with PerformanceTimer() as total_timer:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_search, query) for query in queries]
                results = [future.result() for future in as_completed(futures)]
        
        # Analyze results
        status_codes = [result[0] for result in results]
        times = [result[1] for result in results]
        
        success_rate = sum(1 for code in status_codes if code == 200) / len(status_codes)
        avg_time = statistics.mean(times)
        total_time = total_timer.duration
        
        # Assertions
        assert success_rate >= 0.9, f"Search success rate {success_rate:.2%} below 90%"
        assert avg_time < 3.0, f"Average search time {avg_time:.3f}s exceeds 3s"
        
        print(f"Concurrent searches - Success: {success_rate:.2%}, "
              f"Avg time: {avg_time:.3f}s, Total: {total_time:.3f}s")
    
    @pytest.mark.slow
    def test_concurrent_indexing(self, performance_client, mock_fast_ark_client):
        """Test performance under concurrent indexing load."""
        with patch('src.main.ark_client', mock_fast_ark_client):
            pages = [
                {
                    "url": f"https://example.com/concurrent-{i}",
                    "title": f"Concurrent Test Page {i}",
                    "content": f"Content for concurrent test page {i}",
                    "metadata": {"test": "concurrent"}
                }
                for i in range(10)
            ]
            
            def index_page(page):
                with PerformanceTimer() as timer:
                    response = performance_client.post("/index", json=page)
                    return response.status_code, timer.duration
            
            # Execute concurrent indexing
            with PerformanceTimer() as total_timer:
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [executor.submit(index_page, page) for page in pages]
                    results = [future.result() for future in as_completed(futures)]
            
            # Analyze results
            status_codes = [result[0] for result in results]
            times = [result[1] for result in results]
            
            success_rate = sum(1 for code in status_codes if code in [200, 400]) / len(status_codes)
            avg_time = statistics.mean(times)
            total_time = total_timer.duration
            
            # Assertions for concurrent indexing
            assert success_rate >= 0.8, f"Indexing success rate {success_rate:.2%} below 80%"
            assert avg_time < 10.0, f"Average indexing time {avg_time:.3f}s exceeds 10s"
            
            print(f"Concurrent indexing - Success: {success_rate:.2%}, "
                  f"Avg time: {avg_time:.3f}s, Total: {total_time:.3f}s")


@pytest.mark.performance
class TestMemoryPerformance:
    """Performance tests for memory usage."""
    
    def test_memory_usage_baseline(self, performance_client):
        """Test baseline memory usage."""
        process = psutil.Process(os.getpid())
        
        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform some operations
        for _ in range(10):
            performance_client.get("/health")
            performance_client.get("/search", params={"query": "test"})
        
        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 50, f"Memory increased by {memory_increase:.1f}MB"
        
        print(f"Memory usage - Initial: {initial_memory:.1f}MB, "
              f"Final: {final_memory:.1f}MB, Increase: {memory_increase:.1f}MB")
    
    @pytest.mark.slow
    def test_memory_leak_detection(self, performance_client, mock_fast_ark_client):
        """Test for memory leaks during repeated operations."""
        with patch('src.main.ark_client', mock_fast_ark_client):
            process = psutil.Process(os.getpid())
            memory_readings = []
            
            # Take memory readings during repeated operations
            for i in range(20):
                # Perform operations
                performance_client.get("/health")
                performance_client.get("/search", params={"query": f"test{i}"})
                
                if mock_fast_ark_client:
                    page_data = {
                        "url": f"https://example.com/leak-test-{i}",
                        "title": f"Leak Test {i}",
                        "content": f"Content for leak test {i}",
                        "metadata": {"test": "leak"}
                    }
                    performance_client.post("/index", json=page_data)
                
                # Record memory usage every 5 iterations
                if i % 5 == 0:
                    memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_readings.append(memory)
                    time.sleep(0.1)  # Small delay
            
            # Check for memory leak (significant upward trend)
            if len(memory_readings) >= 3:
                memory_trend = memory_readings[-1] - memory_readings[0]
                # Allow some memory growth but not excessive
                assert memory_trend < 100, f"Potential memory leak: {memory_trend:.1f}MB increase"
                
                print(f"Memory trend over {len(memory_readings)} readings: "
                      f"{memory_readings[0]:.1f}MB -> {memory_readings[-1]:.1f}MB "
                      f"({memory_trend:+.1f}MB)")


@pytest.mark.performance
class TestScalabilityPerformance:
    """Performance tests for scalability."""
    
    @pytest.mark.slow
    def test_large_dataset_search(self, performance_client, mock_fast_ark_client, sample_pages_bulk):
        """Test search performance with large dataset."""
        with patch('src.main.ark_client', mock_fast_ark_client):
            # Index a subset of pages (to avoid timeout)
            pages_to_index = sample_pages_bulk[:20]
            
            index_times = []
            for page in pages_to_index:
                with PerformanceTimer() as timer:
                    response = performance_client.post("/index", json=page)
                    if response.status_code == 200:
                        index_times.append(timer.duration)
            
            # Test search performance after indexing
            search_queries = ["performance", "test", "content", "author", "category"]
            search_times = []
            
            for query in search_queries:
                with PerformanceTimer() as timer:
                    response = performance_client.get("/search", params={"query": query})
                    assert response.status_code == 200
                search_times.append(timer.duration)
            
            if index_times:
                avg_index_time = statistics.mean(index_times)
                print(f"Large dataset indexing - Avg: {avg_index_time:.3f}s per page")
            
            avg_search_time = statistics.mean(search_times)
            max_search_time = max(search_times)
            
            # Search should remain fast even with more data
            assert avg_search_time < 3.0, f"Search degraded to {avg_search_time:.3f}s"
            assert max_search_time < 5.0, f"Worst search time {max_search_time:.3f}s"
            
            print(f"Large dataset search - Avg: {avg_search_time:.3f}s, "
                  f"Max: {max_search_time:.3f}s")
    
    def test_pagination_performance(self, performance_client):
        """Test performance of paginated results."""
        # Test getting all pages (which could be large)
        with PerformanceTimer() as timer:
            response = performance_client.get("/pages")
            assert response.status_code == 200
        
        pages = response.json()
        fetch_time = timer.duration
        
        # Should handle even large page lists efficiently
        assert fetch_time < 2.0, f"Page listing took {fetch_time:.3f}s"
        
        print(f"Page listing - {len(pages)} pages in {fetch_time:.3f}s")


@pytest.mark.performance
class TestAsyncPerformance:
    """Performance tests for async operations."""
    
    @pytest.mark.asyncio
    async def test_async_concurrent_requests(self):
        """Test async performance with many concurrent requests."""
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            # Create many concurrent health checks
            tasks = []
            num_requests = 100
            
            async def make_request():
                start_time = time.perf_counter()
                response = await client.get("/health")
                end_time = time.perf_counter()
                return response.status_code, end_time - start_time
            
            # Execute all requests concurrently
            start_time = time.perf_counter()
            for _ in range(num_requests):
                tasks.append(make_request())
            
            results = await asyncio.gather(*tasks)
            total_time = time.perf_counter() - start_time
            
            # Analyze results
            status_codes = [result[0] for result in results]
            times = [result[1] for result in results]
            
            success_rate = sum(1 for code in status_codes if code == 200) / len(status_codes)
            avg_time = statistics.mean(times)
            throughput = num_requests / total_time
            
            # Async should handle high concurrency well
            assert success_rate >= 0.95, f"Async success rate {success_rate:.2%} below 95%"
            assert throughput > 50, f"Async throughput {throughput:.1f} req/s below 50 req/s"
            
            print(f"Async performance - {num_requests} requests in {total_time:.3f}s, "
                  f"Throughput: {throughput:.1f} req/s, Success: {success_rate:.2%}")


@pytest.mark.performance
def test_performance_summary(performance_client):
    """Generate a performance summary report."""
    print("\n" + "="*60)
    print("PERFORMANCE TEST SUMMARY")
    print("="*60)
    
    # Test key endpoints
    endpoints = {
        "/health": "GET",
        "/search?query=test": "GET",
        "/pages": "GET",
        "/analytics/frequency": "GET",
        "/cache/status": "GET"
    }
    
    results = {}
    for endpoint, method in endpoints.items():
        times = []
        for _ in range(5):
            with PerformanceTimer() as timer:
                if method == "GET":
                    if "?" in endpoint:
                        path, params = endpoint.split("?", 1)
                        param_dict = dict(p.split("=") for p in params.split("&"))
                        response = performance_client.get(path, params=param_dict)
                    else:
                        response = performance_client.get(endpoint)
                else:
                    response = performance_client.post(endpoint)
            times.append(timer.duration)
        
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        
        results[endpoint] = {
            "avg": avg_time,
            "min": min_time,
            "max": max_time
        }
        
        print(f"{endpoint:30} - Avg: {avg_time:.3f}s, "
              f"Min: {min_time:.3f}s, Max: {max_time:.3f}s")
    
    print("="*60)
    
    # Return results for potential use in CI/CD
    return results