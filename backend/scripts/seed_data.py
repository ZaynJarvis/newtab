#!/usr/bin/env python3
"""Seed data script for New Tab Backend."""

import asyncio
import json
import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.database import Database
from src.core.models import PageCreate
from src.services.vector_store import VectorStore
from src.services.api_client import ArkAPIClient
from src.core.config import settings


SAMPLE_PAGES = [
    {
        "url": "https://fastapi.tiangolo.com/",
        "title": "FastAPI - Modern, fast web framework for building APIs",
        "content": """
        FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.7+ 
        based on standard Python type hints. Key features include automatic API documentation, 
        data validation, serialization, and OAuth2 integration. It's designed to be easy to use 
        and learn, with great editor support and minimal code duplication.
        """,
        "favicon_url": "https://fastapi.tiangolo.com/img/favicon.png"
    },
    {
        "url": "https://docs.python.org/3/",
        "title": "Python 3 Documentation",
        "content": """
        The official Python 3 documentation covers the Python language reference, library reference, 
        tutorials, and guides. Python is an interpreted, high-level programming language with 
        dynamic semantics and elegant syntax. It supports multiple programming paradigms and 
        has a comprehensive standard library.
        """,
        "favicon_url": "https://docs.python.org/3/_static/py.png"
    },
    {
        "url": "https://sqlite.org/",
        "title": "SQLite - Lightweight Database Engine",
        "content": """
        SQLite is a C-language library that implements a small, fast, self-contained, 
        high-reliability, full-featured, SQL database engine. It's the most used database 
        engine in the world and is built into all mobile phones and most computers. 
        SQLite supports full-text search with FTS5 extension.
        """,
        "favicon_url": "https://sqlite.org/favicon.ico"
    },
    {
        "url": "https://numpy.org/",
        "title": "NumPy - Scientific Computing with Python",
        "content": """
        NumPy is the fundamental package for scientific computing with Python. It provides 
        a powerful N-dimensional array object, sophisticated broadcasting functions, 
        linear algebra routines, and tools for integrating C/C++ and Fortran code. 
        NumPy forms the foundation of the Python scientific computing ecosystem.
        """,
        "favicon_url": "https://numpy.org/images/logo.svg"
    },
    {
        "url": "https://github.com/",
        "title": "GitHub - Code Collaboration Platform",
        "content": """
        GitHub is a web-based version control and collaboration platform for software developers. 
        It provides Git repository hosting, project management tools, code review features, 
        and social coding capabilities. GitHub hosts millions of open source and private 
        repositories and is essential for modern software development workflows.
        """,
        "favicon_url": "https://github.com/favicon.ico"
    }
]


async def seed_database():
    """Seed the database with sample pages."""
    print("🌱 Seeding New Tab Backend with sample data...")
    
    try:
        # Initialize components
        print("📊 Initializing database...")
        db = Database()
        
        print("🔮 Initializing vector store...")
        vector_store = VectorStore(dimension=settings.vector_dimension)
        
        # Initialize API client if token is available
        ark_client = None
        try:
            ark_client = ArkAPIClient(settings)
            print("✅ API client initialized - will generate real embeddings")
        except Exception as e:
            print(f"⚠️  API client failed to initialize: {e}")
            print("🔄 Will use mock embeddings")
        
        # Insert sample pages
        for i, page_data in enumerate(SAMPLE_PAGES, 1):
            print(f"\n📄 Processing page {i}/{len(SAMPLE_PAGES)}: {page_data['title'][:50]}...")
            
            page = PageCreate(**page_data)
            
            # Insert basic page data
            page_id = db.insert_page(page)
            print(f"   ✅ Inserted page with ID: {page_id}")
            
            if ark_client:
                try:
                    # Generate AI description and keywords
                    print("   🤖 Generating AI keywords and description...")
                    ai_data = await ark_client.generate_keywords_and_description(
                        page.title, page.content
                    )
                    
                    # Generate vector embedding
                    print("   🔮 Generating vector embedding...")
                    embedding_text = f"{page.title} {ai_data['description']} {page.content[:1000]}"
                    vector_embedding = await ark_client.generate_embedding(embedding_text)
                    
                    # Update database with AI-generated data
                    vector_json = json.dumps(vector_embedding) if vector_embedding else None
                    with db.get_connection() as conn:
                        conn.execute("""
                            UPDATE pages 
                            SET description = ?, keywords = ?, vector_embedding = ?
                            WHERE id = ?
                        """, (ai_data['description'], ai_data['keywords'], 
                              vector_json, page_id))
                        conn.commit()
                    
                    # Add to vector store
                    if vector_embedding:
                        updated_page = db.get_page_by_id(page_id)
                        if updated_page:
                            vector_store.add_vector(page_id, vector_embedding, updated_page)
                            print("   ✅ Added to vector store")
                    
                    print(f"   📝 Keywords: {ai_data['keywords'][:100]}...")
                    print(f"   📖 Description: {ai_data['description'][:100]}...")
                    
                except Exception as e:
                    print(f"   ❌ AI processing failed: {e}")
            else:
                print("   ⏭️  Skipped AI processing (no API client)")
            
            # Update page index time
            db.update_page_index_time(page_id)
        
        # Display final statistics
        print(f"\n📊 Seeding completed!")
        print(f"   📄 Total pages: {db.get_total_pages()}")
        print(f"   🔮 Vector store size: {vector_store.size()}")
        
        if ark_client:
            cache_stats = ark_client.get_cache_stats()
            print(f"   💾 Query cache: {cache_stats['size']} entries")
        
        print(f"\n✅ Database seeded successfully!")
        print(f"🚀 Start the server with: python -m src.main")
        print(f"🔍 Test search with: curl \"http://localhost:8000/search?q=python\"")
        
    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print("New Tab Backend - Data Seeding Script")
        print("")
        print("This script populates the database with sample web pages for testing.")
        print("")
        print("Usage:")
        print("  python scripts/seed_data.py")
        print("  uv run python scripts/seed_data.py")
        print("")
        print("Environment:")
        print("  ARK_API_TOKEN - ByteDance ARK API token (optional)")
        print("                  If not set, will use mock embeddings")
        print("")
        print("Sample pages include:")
        for page in SAMPLE_PAGES:
            print(f"  • {page['title']}")
        return
    
    # Check if API token is available
    try:
        token_configured = bool(settings.ark_api_token)
        print(f"🔑 API Token: {'✅ Configured' if token_configured else '❌ Not set (will use mocks)'}")
    except:
        print("🔑 API Token: ❌ Not set (will use mocks)")
    
    # Run the seeding process
    asyncio.run(seed_database())


if __name__ == "__main__":
    main()