#!/usr/bin/env python3
"""Mock data generator for testing the Local Web Memory backend."""

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict
import httpx

# Sample web page data for testing
SAMPLE_PAGES = [
    {
        "url": "https://fastapi.tiangolo.com/tutorial/first-steps/",
        "title": "First Steps - FastAPI",
        "content": """FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints. The key features are: Fast: Very high performance, on par with NodeJS and Go (thanks to Starlette and Pydantic). Fast to code: Increase the speed to develop features by about 200% to 300%. Fewer bugs: Reduce about 40% of human (developer) induced errors. Intuitive: Great editor support. Completion everywhere. Less time debugging. Easy: Designed to be easy to use and learn. Less time reading docs. Short: Minimize code duplication. Multiple features from each parameter declaration. Fewer bugs. Robust: Get production-ready code. With automatic interactive documentation.""",
        "favicon_url": "https://fastapi.tiangolo.com/img/favicon.png"
    },
    {
        "url": "https://python.org/dev/pep/pep-8/",
        "title": "PEP 8 -- Style Guide for Python Code",
        "content": """This document gives coding conventions for the Python code comprising the standard library in the main Python distribution. Please see the companion informational PEP describing style guidelines for the C code in the C implementation of Python. This document and PEP 257 (Docstring Conventions) were adapted from Guido's original Python Style Guide essay, with some additions from Barry's style guide. This style guide evolves over time as additional conventions are identified and past conventions are rendered obsolete by changes in the language itself.""",
        "favicon_url": "https://python.org/static/favicon.ico"
    },
    {
        "url": "https://docs.python.org/3/library/sqlite3.html",
        "title": "sqlite3 — DB-API 2.0 interface for SQLite databases",
        "content": """SQLite is a C library that provides a lightweight disk-based database that doesn't require a separate server process and allows accessing the database using a nonstandard variant of the SQL query language. Some applications can use SQLite for internal data storage. It's also possible to prototype an application using SQLite and then port the code to a larger database such as PostgreSQL or Oracle. The sqlite3 module was written by Gerhard Häring. It provides a SQL interface compliant with the DB-API 2.0 specification described by PEP 249.""",
        "favicon_url": "https://docs.python.org/3/_static/favicon.ico"
    },
    {
        "url": "https://numpy.org/doc/stable/user/quickstart.html",
        "title": "NumPy quickstart — NumPy Manual",
        "content": """NumPy is the fundamental package for scientific computing in Python. It is a Python library that provides a multidimensional array object, various derived objects (such as masked arrays and matrices), and an assortment of routines for fast operations on arrays, including mathematical, logical, shape manipulation, sorting, selecting, I/O, discrete Fourier transforms, basic linear algebra, basic statistical operations, random simulation and much more.""",
        "favicon_url": "https://numpy.org/favicon.ico"
    },
    {
        "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "title": "Artificial intelligence - Wikipedia",
        "content": """Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to natural intelligence displayed by humans and animals. Leading AI textbooks define the field as the study of 'intelligent agents': any device that perceives its environment and takes actions that maximize its chance of successfully achieving its goals. Colloquially, the term 'artificial intelligence' is often used to describe machines (or computers) that mimic 'cognitive' functions that humans associate with the human mind, such as 'learning' and 'problem solving'.""",
        "favicon_url": "https://en.wikipedia.org/static/favicon/wikipedia.ico"
    },
    {
        "url": "https://github.com/features/actions",
        "title": "GitHub Actions - GitHub Features",
        "content": """GitHub Actions makes it easy to automate all your software workflows, now with world-class CI/CD. Build, test, and deploy your code right from GitHub. Make code reviews, branch management, and issue triaging work the way you want. Whether you want to build a container, deploy a web service, or automate welcoming new users to your open source projects—there's an action for that. Combine and configure actions for the services you use, built and maintained by the community.""",
        "favicon_url": "https://github.githubassets.com/favicon.ico"
    },
    {
        "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
        "title": "JavaScript - MDN Web Docs",
        "content": """JavaScript (JS) is a lightweight, interpreted, or just-in-time compiled programming language with first-class functions. While it is most well-known as the scripting language for Web pages, many non-browser environments also use it, such as Node.js, Apache CouchDB and Adobe Acrobat. JavaScript is a prototype-based, multi-paradigm, single-threaded, dynamic language, supporting object-oriented, imperative, and declarative (e.g. functional programming) styles.""",
        "favicon_url": "https://developer.mozilla.org/favicon-192x192.png"
    },
    {
        "url": "https://stackoverflow.com/questions/11227809/why-is-processing-a-sorted-array-faster-than-processing-an-unsorted-array",
        "title": "Why is processing a sorted array faster than processing an unsorted array?",
        "content": """You are a victim of branch prediction fail. What is Branch Prediction? Consider a railroad junction. Now for the sake of argument, suppose this is back in the 1800s - before long distance or radio communication. You are the operator of a junction and you hear a train coming. You have no idea which way it is supposed to go. You stop the train to ask the driver which direction they want. And then you set the switch appropriately. Trains are heavy and have a lot of inertia. So they take forever to start up and slow down.""",
        "favicon_url": "https://cdn.sstatic.net/Sites/stackoverflow/Img/favicon.ico"
    },
    {
        "url": "https://react.dev/learn",
        "title": "Learn React",
        "content": """React is a JavaScript library for building user interfaces. Learn what React is all about on our homepage or in the tutorial. This page will give you an introduction to the 80% of React concepts that you will use on a daily basis. You will learn: How to create and nest components, How to add markup and styles, How to display data, How to render conditions and lists, How to respond to events and update the screen, How to share data between components.""",
        "favicon_url": "https://react.dev/favicon.ico"
    },
    {
        "url": "https://www.tensorflow.org/tutorials",
        "title": "TensorFlow Tutorials",
        "content": """TensorFlow is an end-to-end open source platform for machine learning. It has a comprehensive, flexible ecosystem of tools, libraries and community resources that lets researchers push the state-of-the-art in ML and developers easily build and deploy ML powered applications. TensorFlow offers multiple levels of abstraction so you can choose the right one for your needs. Build and train models by using the high-level Keras API, which makes getting started with machine learning and TensorFlow easy.""",
        "favicon_url": "https://www.tensorflow.org/favicon.ico"
    }
]


class MockDataGenerator:
    """Generate mock data for testing the Local Web Memory backend."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the mock data generator."""
        self.base_url = base_url
        self.client = None
    
    async def create_client(self):
        """Create HTTP client."""
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close_client(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
    
    async def check_backend_health(self) -> bool:
        """Check if the backend is running and healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Backend health check failed: {e}")
            return False
    
    async def index_page(self, page_data: Dict) -> Dict:
        """Index a single page."""
        try:
            response = await self.client.post(
                f"{self.base_url}/index",
                json=page_data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Failed to index page {page_data.get('url', 'unknown')}: {e}")
            return None
    
    async def search_keyword(self, query: str, limit: int = 5) -> Dict:
        """Perform keyword search."""
        try:
            response = await self.client.get(
                f"{self.base_url}/search/keyword",
                params={"query": query, "limit": limit}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Keyword search failed for '{query}': {e}")
            return None
    
    async def search_vector(self, query: str, limit: int = 5) -> Dict:
        """Perform vector search."""
        try:
            response = await self.client.get(
                f"{self.base_url}/search/vector",
                params={"query": query, "limit": limit, "min_similarity": 0.1}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Vector search failed for '{query}': {e}")
            return None
    
    async def get_all_pages(self) -> List[Dict]:
        """Get all indexed pages."""
        try:
            response = await self.client.get(f"{self.base_url}/pages")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Failed to get pages: {e}")
            return []
    
    async def get_stats(self) -> Dict:
        """Get system statistics."""
        try:
            response = await self.client.get(f"{self.base_url}/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Failed to get stats: {e}")
            return {}
    
    async def generate_and_index_sample_data(self, num_pages: int = None):
        """Generate and index sample pages."""
        pages_to_use = SAMPLE_PAGES if num_pages is None else SAMPLE_PAGES[:num_pages]
        
        print(f"🚀 Indexing {len(pages_to_use)} sample pages...")
        
        indexed_count = 0
        for i, page in enumerate(pages_to_use, 1):
            print(f"📄 Indexing page {i}/{len(pages_to_use)}: {page['title']}")
            
            result = await self.index_page(page)
            if result:
                indexed_count += 1
                print(f"   ✅ Indexed with ID {result.get('id')} in {result.get('processing_time', 0):.1f}ms")
            
            # Small delay to avoid overwhelming the backend
            await asyncio.sleep(0.5)
        
        print(f"📊 Successfully indexed {indexed_count}/{len(pages_to_use)} pages")
        return indexed_count
    
    async def run_search_tests(self):
        """Run various search tests."""
        test_queries = [
            "Python programming",
            "machine learning",
            "web development",
            "JavaScript tutorial",
            "artificial intelligence",
            "database sqlite",
            "FastAPI framework",
            "GitHub actions",
            "React components"
        ]
        
        print("\n🔍 Running keyword search tests...")
        for query in test_queries[:5]:  # Test first 5 queries
            print(f"\n📝 Keyword search: '{query}'")
            results = await self.search_keyword(query)
            
            if results:
                print(f"   Found {results.get('total_found', 0)} results")
                for result in results.get('results', [])[:3]:  # Show top 3
                    print(f"   - {result.get('title', 'No title')}")
            else:
                print("   No results")
        
        print("\n🎯 Running vector search tests...")
        for query in test_queries[:3]:  # Test first 3 queries for vector search
            print(f"\n🔍 Vector search: '{query}'")
            results = await self.search_vector(query)
            
            if results:
                print(f"   Found {results.get('total_found', 0)} results")
                for result in results.get('results', [])[:3]:  # Show top 3
                    title = result.get('title', 'No title')
                    similarity = result.get('similarity_score', 0)
                    print(f"   - {title} (similarity: {similarity:.3f})")
            else:
                print("   No results or vector search unavailable")
    
    async def show_stats(self):
        """Display system statistics."""
        print("\n📊 System Statistics:")
        stats = await self.get_stats()
        
        if stats:
            db_stats = stats.get('database', {})
            vector_stats = stats.get('vector_store', {})
            api_stats = stats.get('api_client', {})
            
            print(f"   Database pages: {db_stats.get('total_pages', 0)}")
            print(f"   Vector store: {vector_stats.get('total_vectors', 0)} vectors")
            print(f"   Memory usage: {vector_stats.get('memory_usage_mb', 0)} MB")
            print(f"   API client: {api_stats.get('status', 'unknown')}")
    
    async def run_performance_test(self, num_requests: int = 10):
        """Run performance tests."""
        print(f"\n⚡ Running performance test with {num_requests} requests...")
        
        # Test keyword search performance
        start_time = time.time()
        tasks = []
        
        for i in range(num_requests):
            query = random.choice(["Python", "JavaScript", "AI", "web", "database"])
            tasks.append(self.search_keyword(query))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        successful_requests = sum(1 for r in results if r and not isinstance(r, Exception))
        
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Average time per request: {(total_time / num_requests) * 1000:.1f}ms")
        print(f"   Successful requests: {successful_requests}/{num_requests}")
        print(f"   Requests per second: {num_requests / total_time:.1f}")


async def main():
    """Main function to run the mock data generator."""
    print("🔧 Local Web Memory Backend - Mock Data Generator")
    print("=" * 60)
    
    generator = MockDataGenerator()
    await generator.create_client()
    
    try:
        # Check if backend is running
        print("🏥 Checking backend health...")
        if not await generator.check_backend_health():
            print("❌ Backend is not running. Please start it first:")
            print("   cd backend && uv run python main.py")
            return
        
        print("✅ Backend is running and healthy!")
        
        # Show initial stats
        await generator.show_stats()
        
        # Index sample data
        await generator.generate_and_index_sample_data()
        
        # Wait a bit for background AI processing
        print("\n⏳ Waiting 5 seconds for AI processing to complete...")
        await asyncio.sleep(5)
        
        # Show updated stats
        await generator.show_stats()
        
        # Run search tests
        await generator.run_search_tests()
        
        # Run performance test
        await generator.run_performance_test()
        
        print("\n✅ Mock data generation and testing completed!")
        print("🌐 You can now test the API at: http://localhost:8000/docs")
    
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
    finally:
        await generator.close_client()


if __name__ == "__main__":
    asyncio.run(main())