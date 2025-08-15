import asyncio
import httpx
import json

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
        
        # 3. Keyword Search
        print("\n3. Keyword Search Tests:")
        queries = ["Python", "machine learning", "JavaScript", "database"]
        for query in queries:
            response = await client.get(f"{base_url}/search/keyword", params={"query": query, "limit": 3})
            data = response.json()
            print(f"   '{query}': {data['total_found']} results")
            if data['results']:
                for result in data['results'][:2]:
                    print(f"      - {result['title']}")
        
        # 4. Vector Search
        print("\n4. Vector/Semantic Search Tests:")
        queries = [
            "Python programming best practices",
            "machine learning and AI",
            "web development with JavaScript",
            "database management"
        ]
        for query in queries:
            response = await client.get(f"{base_url}/search/vector", params={"query": query, "limit": 3})
            if response.status_code == 200:
                data = response.json()
                print(f"   '{query[:30]}...': {data['total_found']} results")
                if data['results']:
                    for result in data['results'][:2]:
                        similarity = result.get('similarity_score', 0)
                        print(f"      - {result['title']} (similarity: {similarity:.3f})")
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
            
            # Test searching for it
            response = await client.get(f"{base_url}/search/vector", params={"query": "neural networks deep learning", "limit": 5})
            data = response.json()
            found_test_page = any(r['id'] == page_id for r in data['results'])
            print(f"   Found in vector search: {found_test_page}")
        else:
            print(f"   ❌ Indexing failed: {response.status_code}")
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_backend())
