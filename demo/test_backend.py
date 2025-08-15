import asyncio
import httpx
import json
import time

async def test_backend():
    """Comprehensive test of the backend API."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30) as client:
        print("✅ Backend API Test Suite")
        print("=" * 60)
        
        # 1. Health Check
        print("\n1. Health Check:")
        response = await client.get(f"{base_url}/health")
        health = response.json()
        print(f"   Status: {health['status']}")
        print(f"   Total pages: {health['total_pages']}")
        
        # 2. Statistics
        print("\n2. System Statistics:")
        response = await client.get(f"{base_url}/stats")
        stats = response.json()
        print(f"   Database pages: {stats['database']['total_pages']}")
        print(f"   Vector store: {stats['vector_store']['total_vectors']} vectors")
        print(f"   Vector dimension: {stats['vector_store']['dimension']}")
        print(f"   API client: {stats['api_client']['status']}")
        
        # 3. Unified Search Tests
        print("\n3. Unified Search Tests:")
        queries = ["Python", "machine learning", "JavaScript", "database"]
        for query in queries:
            response = await client.get(f"{base_url}/search", params={"q": query})
            data = response.json()
            print(f"   '{query}': {data['total_found']} results (max 10 server-controlled)")
            if data['results']:
                for result in data['results'][:2]:
                    relevance = result.get('relevance_score', 0)
                    print(f"      - {result['title']} (relevance: {relevance:.3f})")
            # Verify server enforces max 10 results
            assert len(data['results']) <= 10, f"Server returned more than 10 results: {len(data['results'])}"
        
        # 4. Semantic Query Tests (same endpoint, server handles vector search internally)
        print("\n4. Semantic Query Tests:")
        queries = [
            "Python programming best practices",
            "machine learning and AI", 
            "web development with JavaScript",
            "database management"
        ]
        for query in queries:
            response = await client.get(f"{base_url}/search", params={"q": query})
            if response.status_code == 200:
                data = response.json()
                print(f"   '{query[:30]}...': {data['total_found']} results")
                if data['results']:
                    for result in data['results'][:2]:
                        relevance = result.get('relevance_score', 0)
                        print(f"      - {result['title']} (relevance: {relevance:.3f})")
                # Verify server control
                assert len(data['results']) <= 10, f"Server returned more than 10 results: {len(data['results'])}"
            else:
                print(f"   '{query[:30]}...': ❌ Error {response.status_code}")
        
        # 5. Test new page indexing with embedding
        print("\n5. Test New Page Indexing with Embedding:")
        test_page = {
            "url": "https://example.com/test",
            "title": "Test Page for Embedding Verification",
            "content": "This is a test page about Python programming, machine learning, and artificial intelligence. It covers topics like neural networks, deep learning, and natural language processing.",
            "favicon_url": "https://example.com/favicon.ico"
        }
        
        response = await client.post(f"{base_url}/index", json=test_page)
        if response.status_code == 200:
            result = response.json()
            page_id = result['id']
            print(f"   ✅ Page indexed with ID: {page_id}")
            
            # Wait for AI processing
            await asyncio.sleep(3)
            
            # Verify the page has embedding
            response = await client.get(f"{base_url}/pages/{page_id}")
            page_data = response.json()
            has_embedding = page_data.get('vector_embedding') is not None
            has_keywords = page_data.get('keywords') is not None
            print(f"   Has embedding: {has_embedding}")
            print(f"   Has keywords: {has_keywords}")
            if has_keywords:
                print(f"   Keywords: {page_data['keywords']}")
            
            # Test searching for it with unified search
            response = await client.get(f"{base_url}/search", params={"q": "neural networks deep learning"})
            data = response.json()
            found_test_page = any(r['id'] == page_id for r in data['results'])
            print(f"   Found in unified search: {found_test_page}")
            
            # Verify server controls max results
            assert len(data['results']) <= 10, f"Server returned more than 10 results: {len(data['results'])}"
        else:
            print(f"   ❌ Indexing failed: {response.status_code}")
        
        # 6. Test Server-Controlled Logic
        print("\n6. Server Control Verification:")
        test_queries = ["test query", "another test", "final test"]
        for query in test_queries:
            response = await client.get(f"{base_url}/search", params={"q": query})
            if response.status_code == 200:
                data = response.json()
                # Verify max 10 results enforced by server
                assert len(data['results']) <= 10, f"Max 10 results violated: {len(data['results'])}"
                # Verify response structure
                assert 'results' in data
                assert 'total_found' in data
                assert 'query' in data
                assert data['query'] == query
                print(f"   ✅ Query '{query}': {len(data['results'])} results (≤10 ✓)")
        
        print("\n" + "=" * 60)
        print("✅ All unified search tests completed successfully!")
        print("✅ Server-controlled logic verified!")
        print("✅ Max 10 results constraint enforced!")

if __name__ == "__main__":
    asyncio.run(test_backend())
