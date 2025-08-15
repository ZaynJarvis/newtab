#!/usr/bin/env python3
"""Quick validation test for the Local Web Memory backend."""

import asyncio
import httpx


async def main():
    """Run quick validation tests."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        print("🧪 Running Quick Backend Validation Tests")
        print("=" * 50)
        
        # Test 1: Health check
        print("1. Health Check...")
        response = await client.get(f"{base_url}/health")
        if response.status_code == 200:
            print("   ✅ Health check passed")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return
        
        # Test 2: Stats
        print("2. Stats...")
        response = await client.get(f"{base_url}/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✅ Stats: {stats['database']['total_pages']} pages, {stats['vector_store']['total_vectors']} vectors")
        else:
            print(f"   ❌ Stats failed: {response.status_code}")
        
        # Test 3: Add a new page
        print("3. Adding new page...")
        test_page = {
            "url": "https://test.example.com/quick-test",
            "title": "Quick Test Page",
            "content": "This is a quick test page for validation. It contains Python and machine learning content.",
            "favicon_url": "https://test.example.com/favicon.ico"
        }
        
        response = await client.post(f"{base_url}/index", json=test_page)
        if response.status_code == 200:
            result = response.json()
            page_id = result['id']
            print(f"   ✅ Page indexed with ID {page_id}")
        else:
            print(f"   ❌ Indexing failed: {response.status_code}")
            return
        
        # Test 4: Wait a moment for AI processing
        print("4. Waiting 2 seconds for AI processing...")
        await asyncio.sleep(2)
        
        # Test 5: Keyword search
        print("5. Keyword search...")
        response = await client.get(f"{base_url}/search/keyword", params={"query": "Python", "limit": 3})
        if response.status_code == 200:
            results = response.json()
            print(f"   ✅ Found {results['total_found']} results for 'Python'")
            for result in results['results'][:2]:
                print(f"      - {result['title']}")
        else:
            print(f"   ❌ Keyword search failed: {response.status_code}")
        
        # Test 6: Vector search
        print("6. Vector search...")
        response = await client.get(f"{base_url}/search/vector", params={"query": "machine learning", "limit": 3})
        if response.status_code == 200:
            results = response.json()
            print(f"   ✅ Vector search completed with {results['total_found']} results")
        else:
            print(f"   ❌ Vector search failed: {response.status_code}")
        
        # Test 7: Get specific page
        print("7. Get specific page...")
        response = await client.get(f"{base_url}/pages/{page_id}")
        if response.status_code == 200:
            page = response.json()
            print(f"   ✅ Retrieved page: {page['title']}")
            print(f"      Description: {page['description'][:60]}...")
            print(f"      Keywords: {page['keywords']}")
        else:
            print(f"   ❌ Page retrieval failed: {response.status_code}")
        
        # Test 8: Delete page
        print("8. Delete test page...")
        response = await client.delete(f"{base_url}/pages/{page_id}")
        if response.status_code == 200:
            print("   ✅ Page deleted successfully")
        else:
            print(f"   ❌ Page deletion failed: {response.status_code}")
        
        print("\n🎉 All tests completed!")
        print(f"🌐 Full API documentation available at: {base_url}/docs")


if __name__ == "__main__":
    asyncio.run(main())