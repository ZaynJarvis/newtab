"""Local Web Memory Backend Service - FastAPI with SQLite FTS5 and vector search."""

import asyncio
import os
import sys
import time
from datetime import datetime
from typing import List, Optional, Dict, Tuple

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models import (
    PageCreate, PageResponse, SearchRequest, UnifiedSearchResponse,
    HealthResponse, IndexResponse
)
from database import Database
from vector_store import VectorStore
from api_client import ArkAPIClient

# Check for required ARK_API_KEY environment variable
ARK_API_KEY = os.getenv("ARK_API_KEY")
if not ARK_API_KEY or ARK_API_KEY.strip() == "":
    print("❌ ERROR: ARK_API_KEY environment variable is required but not set.")
    print("Please set the ARK_API_KEY environment variable before starting the server.")
    print("Example: export ARK_API_KEY=\"your-api-key-here\"")
    sys.exit(1)

# Initialize FastAPI app
app = FastAPI(
    title="Local Web Memory Backend API",
    description="""
    ## 🔍 Local Web Memory Backend Service

    A FastAPI-powered service for local web page indexing and intelligent search with AI-generated keywords and vector embeddings.

    ### Key Features
    - **Intelligent Search**: Unified search combining keyword and semantic similarity
    - **AI-Powered**: ByteDance ARK LLM for keyword generation and embeddings
    - **Local Storage**: SQLite with FTS5 for fast full-text search
    - **Vector Search**: High-dimensional semantic similarity matching
    - **Chrome Extension Ready**: CORS-enabled for browser extension integration

    ### Search Algorithm
    - **Server-Controlled**: Optimal 70% semantic + 30% keyword weighting
    - **Maximum 10 Results**: Curated, relevant results only
    - **Parallel Processing**: Keyword and vector search executed simultaneously
    - **Smart Deduplication**: URL-based result merging with combined scoring

    ### Performance
    - **Low Latency**: Parallel search execution with optimized ranking
    - **Scalable**: Handles 1000+ documents efficiently
    - **Reliable**: Comprehensive error handling and fallback mechanisms
    """,
    version="2.0.0",
    contact={
        "name": "Local Web Memory Team",
        "url": "https://github.com/localwebmemory/backend",
        "email": "support@localwebmemory.dev"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
        "identifier": "MIT"
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "search",
            "description": "Unified search operations combining keyword and semantic search"
        },
        {
            "name": "indexing", 
            "description": "Page indexing and content management"
        },
        {
            "name": "health",
            "description": "Service health and status monitoring"
        }
    ]
)

# Add CORS middleware for Chrome extension access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
db = Database()
vector_store = VectorStore(dimension=2048)  # ByteDance embedding model dimension
ark_client = None

# Initialize Ark API client if API key is available
try:
    ark_client = ArkAPIClient()
    print("✅ Ark API client initialized successfully")
except Exception as e:
    print(f"⚠️  Ark API client initialization failed: {e}")
    print("🔄 Running in mock mode")


async def process_page_ai(page_id: int, page: PageCreate):
    """Background task to process page with AI services."""
    if not ark_client:
        print(f"Skipping AI processing for page {page_id} - no API client")
        return
    
    try:
        # Generate keywords and description
        ai_data = await ark_client.generate_keywords_and_description(page.title, page.content)
        
        # Generate vector embedding
        embedding_text = f"{page.title} {ai_data['description']} {page.content[:1000]}"
        vector_embedding = await ark_client.generate_embedding(embedding_text)
        
        # Update database with AI-generated data
        import json
        vector_json = json.dumps(vector_embedding) if vector_embedding else None
        with db.get_connection() as conn:
            conn.execute("""
                UPDATE pages 
                SET description = ?, keywords = ?, vector_embedding = ?
                WHERE id = ?
            """, (ai_data['description'], ai_data['keywords'], 
                  vector_json, page_id))
            conn.commit()
        
        # Update vector store
        updated_page = db.get_page_by_id(page_id)
        if updated_page and vector_embedding:
            vector_store.add_vector(page_id, vector_embedding, updated_page)
        
        print(f"✅ AI processing completed for page {page_id}")
    
    except Exception as e:
        print(f"❌ AI processing failed for page {page_id}: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    print("🚀 Starting Local Web Memory Backend...")
    
    # Load existing vectors into memory
    try:
        vectors_data = db.get_all_vectors()
        for page_id, vector in vectors_data:
            page_data = db.get_page_by_id(page_id)
            if page_data:
                vector_store.add_vector(page_id, vector, page_data)
        
        print(f"📊 Loaded {len(vectors_data)} vectors into memory")
    except Exception as e:
        print(f"⚠️  Error loading vectors: {e}")
    
    # Test API connection if available
    if ark_client:
        try:
            health = await ark_client.health_check()
            print(f"🔗 API Health: {health['status']}")
        except Exception as e:
            print(f"⚠️  API health check failed: {e}")


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Local Web Memory Backend",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "index": "POST /index",
            "search": "GET /search",
            "pages": "GET /pages",
            "delete_page": "DELETE /pages/{id}"
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Health check endpoint."""
    try:
        total_pages = db.get_total_pages()
        api_status = None
        
        if ark_client:
            try:
                api_health = await ark_client.health_check()
                api_status = api_health.get('status', 'unknown')
            except:
                api_status = 'error'
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            database_connected=True,
            total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.post("/index", response_model=IndexResponse, tags=["indexing"])
async def index_page(page: PageCreate, background_tasks: BackgroundTasks):
    """Index a new web page."""
    start_time = time.time()
    
    try:
        # Insert page with basic data first
        page_id = db.insert_page(page)
        
        # Schedule AI processing in background
        background_tasks.add_task(process_page_ai, page_id, page)
        
        processing_time = time.time() - start_time
        
        return IndexResponse(
            id=page_id,
            status="indexed",
            message="Page indexed successfully. AI processing in progress.",
            processing_time=round(processing_time * 1000, 2)  # Convert to milliseconds
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")












@app.get("/search", response_model=UnifiedSearchResponse, tags=["search"])
async def unified_search(q: str):
    """
    Unified search endpoint with server-controlled ranking logic.
    
    Combines keyword and semantic search with optimal server-side mixing:
    - 70% weight for semantic/vector search (for relevance)
    - 30% weight for keyword/text search (for exact matches)
    - Maximum 10 results returned
    - Server handles all ranking and deduplication
    
    Args:
        q: Search query string
    
    Returns:
        Unified search results with relevance scoring
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Server-controlled parameters
    MAX_RESULTS = 10
    VECTOR_WEIGHT = 0.7
    KEYWORD_WEIGHT = 0.3
    MIN_SIMILARITY = 0.1
    
    # Advanced filtering parameters
    ENABLE_SMART_CUTOFF = True
    SIMILARITY_DROP_THRESHOLD = 0.15  # Detect 15% similarity drops
    MIN_CLUSTER_SCORE = 0.25  # Minimum score for clustering analysis
    
    try:
        # Define async functions for parallel execution
        async def get_keyword_results():
            """Get keyword search results."""
            try:
                results, total = db.search_keyword(q, MAX_RESULTS * 2)
                return results
            except Exception as e:
                print(f"Keyword search error: {e}")
                return []
        
        async def get_vector_results():
            """Get vector search results."""
            if not ark_client:
                return []
            
            try:
                # Generate embedding for query
                query_vector = await ark_client.generate_embedding(q)
                
                # Search in vector store with advanced filtering
                vector_results = vector_store.search(
                    query_vector, 
                    MAX_RESULTS * 2, 
                    MIN_SIMILARITY,
                    enable_clustering=ENABLE_SMART_CUTOFF,
                    similarity_drop_threshold=SIMILARITY_DROP_THRESHOLD
                )
                
                # Format results with similarity scores
                formatted_results = []
                for page_data, similarity in vector_results:
                    result_dict = page_data.dict()
                    result_dict['vector_similarity'] = round(similarity, 4)
                    formatted_results.append(result_dict)
                
                return formatted_results
            except Exception as e:
                print(f"Vector search error: {e}")
                return []
        
        # Execute searches in parallel
        keyword_task = asyncio.create_task(get_keyword_results())
        vector_task = asyncio.create_task(get_vector_results())
        
        # Wait for both searches to complete
        keyword_results, vector_results = await asyncio.gather(keyword_task, vector_task)
        
        # Server-controlled result mixing
        url_to_result = {}
        
        # Process keyword results with position-based scoring
        for i, result in enumerate(keyword_results):
            result_dict = result.dict()
            # Position-based scoring: first result = 1.0, decreasing linearly
            keyword_score = 1.0 - (i / max(len(keyword_results) - 1, 1)) * 0.9 if len(keyword_results) > 1 else 1.0
            result_dict['keyword_score'] = keyword_score
            result_dict['vector_score'] = 0.0
            result_dict['relevance_score'] = keyword_score * KEYWORD_WEIGHT
            url_to_result[result.url] = result_dict
        
        # Process vector results and merge/add
        for result in vector_results:
            url = result['url']
            vector_score = result.get('vector_similarity', 0.0)
            
            if url in url_to_result:
                # Merge with existing keyword result
                existing = url_to_result[url]
                existing['vector_score'] = vector_score
                existing['relevance_score'] = (
                    existing['keyword_score'] * KEYWORD_WEIGHT + 
                    vector_score * VECTOR_WEIGHT
                )
            else:
                # New result from vector search only
                result['keyword_score'] = 0.0
                result['vector_score'] = vector_score
                result['relevance_score'] = vector_score * VECTOR_WEIGHT
                url_to_result[url] = result
        
        # Sort by relevance score and limit to MAX_RESULTS
        final_results = list(url_to_result.values())
        final_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        final_results = final_results[:MAX_RESULTS]
        
        # Clean up results for response - keep only relevance_score
        for result in final_results:
            result['relevance_score'] = round(result['relevance_score'], 4)
            # Remove internal scoring fields
            result.pop('keyword_score', None)
            result.pop('vector_score', None)
            result.pop('vector_similarity', None)
        
        return UnifiedSearchResponse(
            results=final_results,
            total_found=len(final_results),
            query=q
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/pages", response_model=List[PageResponse], tags=["indexing"])
async def get_pages(limit: int = 100, offset: int = 0):
    """Get all pages with pagination."""
    if limit > 1000:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 1000")
    
    try:
        pages = db.get_all_pages(limit, offset)
        return pages
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve pages: {str(e)}")


@app.get("/pages/{page_id}", response_model=PageResponse, tags=["indexing"])
async def get_page(page_id: int):
    """Get a specific page by ID."""
    page = db.get_page_by_id(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return page


@app.delete("/pages/{page_id}", response_model=dict, tags=["indexing"])
async def delete_page(page_id: int):
    """Delete a specific page by ID."""
    try:
        # Remove from vector store
        vector_store.remove_vector(page_id)
        
        # Remove from database
        deleted = db.delete_page(page_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Page not found")
        
        return {
            "status": "deleted",
            "page_id": page_id,
            "message": "Page deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete page: {str(e)}")


@app.get("/stats", response_model=dict, tags=["health"])
async def get_stats():
    """Get system statistics."""
    try:
        total_pages = db.get_total_pages()
        vector_stats = vector_store.get_stats()
        
        return {
            "database": {
                "total_pages": total_pages
            },
            "vector_store": vector_stats,
            "api_client": {
                "configured": ark_client is not None,
                "status": "available" if ark_client else "unavailable"
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Local Web Memory Backend Server...")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
