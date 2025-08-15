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
    PageCreate, PageResponse, SearchRequest, KeywordSearchResponse,
    VectorSearchResponse, CombinedSearchResponse, HealthResponse, IndexResponse
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
    title="Local Web Memory Backend",
    description="FastAPI service for local web page indexing and search with AI-generated keywords and vector embeddings",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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
            "search_keyword": "GET /search/keyword",
            "search_vector": "GET /search/vector",
            "search_combined": "GET /search/combined",
            "pages": "GET /pages",
            "delete_page": "DELETE /pages/{id}"
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", response_model=HealthResponse)
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


@app.post("/index", response_model=IndexResponse)
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


@app.get("/search/keyword", response_model=KeywordSearchResponse)
async def search_keyword(query: str, limit: int = 10):
    """Search pages using keyword/full-text search."""
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        results, total_found = db.search_keyword(query, limit)
        
        return KeywordSearchResponse(
            results=results,
            total_found=total_found,
            query=query
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Keyword search failed: {str(e)}")


@app.get("/search/vector", response_model=VectorSearchResponse)
async def search_vector(query: str, limit: int = 10, min_similarity: float = 0.1):
    """Search pages using vector similarity."""
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    if not ark_client:
        raise HTTPException(status_code=503, detail="Vector search unavailable - API client not configured")
    
    try:
        # Generate embedding for query
        query_vector = await ark_client.generate_embedding(query)
        
        # Search in vector store
        results = vector_store.search(query_vector, limit, min_similarity)
        
        # Format results with similarity scores
        formatted_results = []
        for page_data, similarity in results:
            result_dict = page_data.dict()
            result_dict['similarity_score'] = round(similarity, 4)
            formatted_results.append(result_dict)
        
        return VectorSearchResponse(
            results=formatted_results,
            total_found=len(formatted_results),
            query=query
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector search failed: {str(e)}")


@app.get("/search/combined", response_model=CombinedSearchResponse)
async def search_combined(
    query: str, 
    limit: int = 10, 
    min_similarity: float = 0.1,
    keyword_weight: float = 0.6,
    semantic_weight: float = 0.4
):
    """
    Combined search using both keyword and semantic search with weighted scoring.
    
    Args:
        query: Search query
        limit: Maximum number of results to return
        min_similarity: Minimum similarity threshold for vector search
        keyword_weight: Weight for keyword search results (default: 0.6)
        semantic_weight: Weight for semantic search results (default: 0.4)
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Validate weights
    if abs(keyword_weight + semantic_weight - 1.0) > 0.001:
        raise HTTPException(status_code=400, detail="Keyword weight and semantic weight must sum to 1.0")
    
    try:
        # Define async functions for parallel execution
        async def get_keyword_results():
            """Get keyword search results."""
            try:
                results, total = db.search_keyword(query, limit * 2)  # Get more results for better merging
                return results, total
            except Exception as e:
                print(f"Keyword search error: {e}")
                return [], 0
        
        async def get_vector_results():
            """Get vector search results."""
            if not ark_client:
                return [], 0
            
            try:
                # Generate embedding for query
                query_vector = await ark_client.generate_embedding(query)
                
                # Search in vector store
                vector_results = vector_store.search(query_vector, limit * 2, min_similarity)
                
                # Format results with similarity scores
                formatted_results = []
                for page_data, similarity in vector_results:
                    result_dict = page_data.dict()
                    result_dict['similarity_score'] = round(similarity, 4)
                    formatted_results.append(result_dict)
                
                return formatted_results, len(formatted_results)
            except Exception as e:
                print(f"Vector search error: {e}")
                return [], 0
        
        # Execute searches in parallel
        keyword_task = asyncio.create_task(get_keyword_results())
        vector_task = asyncio.create_task(get_vector_results())
        
        # Wait for both searches to complete
        (keyword_results, keyword_total), (vector_results, vector_total) = await asyncio.gather(
            keyword_task, vector_task
        )
        
        # Normalize and combine scores
        combined_results = _combine_search_results(
            keyword_results, vector_results, keyword_weight, semantic_weight
        )
        
        # Limit final results
        final_results = combined_results[:limit]
        
        return CombinedSearchResponse(
            results=final_results,
            total_found=len(final_results),
            query=query,
            keyword_results_count=len(keyword_results),
            semantic_results_count=len(vector_results)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Combined search failed: {str(e)}")


def _normalize_keyword_scores(results: List[PageResponse]) -> List[Dict]:
    """Normalize keyword search scores to 0-1 range using ranking position."""
    if not results:
        return []
    
    result_dicts = []
    
    # Since results from db.search_keyword() are already ranked by BM25 score,
    # we can assign scores based on ranking position (1st = highest score)
    total_results = len(results)
    
    for i, result in enumerate(results):
        result_dict = result.dict()
        
        # Assign scores based on ranking position (0-based index)
        # First result gets highest score (1.0), last gets lowest
        if total_results == 1:
            normalized_score = 1.0
        else:
            # Linear decay from 1.0 to 0.1 based on position
            normalized_score = 1.0 - (i / (total_results - 1)) * 0.9
        
        result_dict['normalized_keyword_score'] = round(normalized_score, 4)
        result_dict['ranking_position'] = i + 1  # 1-based ranking
        result_dicts.append(result_dict)
    
    return result_dicts


def _combine_search_results(
    keyword_results: List[PageResponse], 
    vector_results: List[Dict], 
    keyword_weight: float, 
    semantic_weight: float
) -> List[Dict]:
    """
    Combine and deduplicate search results with weighted scoring.
    
    Args:
        keyword_results: Results from keyword search
        vector_results: Results from vector search (already formatted as dicts)
        keyword_weight: Weight for keyword search scores
        semantic_weight: Weight for semantic search scores
    
    Returns:
        Combined and ranked results
    """
    # Normalize keyword scores
    normalized_keyword_results = _normalize_keyword_scores(keyword_results)
    
    # Create URL-based lookup for deduplication
    url_to_result: Dict[str, Dict] = {}
    
    # Add keyword results
    for result in normalized_keyword_results:
        url = result['url']
        result['keyword_score'] = result.get('normalized_keyword_score', 0.0)
        result['semantic_score'] = 0.0
        result['combined_score'] = result['keyword_score'] * keyword_weight
        url_to_result[url] = result
    
    # Add or merge vector results
    for result in vector_results:
        url = result['url']
        semantic_score = result.get('similarity_score', 0.0)
        
        if url in url_to_result:
            # URL already exists from keyword search, merge scores
            existing = url_to_result[url]
            existing['semantic_score'] = semantic_score
            existing['combined_score'] = (
                existing['keyword_score'] * keyword_weight + 
                semantic_score * semantic_weight
            )
        else:
            # New URL from vector search only
            result['keyword_score'] = 0.0
            result['semantic_score'] = semantic_score
            result['combined_score'] = semantic_score * semantic_weight
            url_to_result[url] = result
    
    # Sort by combined score (descending) and return
    combined_results = list(url_to_result.values())
    combined_results.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # Round combined scores for cleaner output
    for result in combined_results:
        result['combined_score'] = round(result['combined_score'], 4)
    
    return combined_results


@app.get("/pages", response_model=List[PageResponse])
async def get_pages(limit: int = 100, offset: int = 0):
    """Get all pages with pagination."""
    if limit > 1000:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 1000")
    
    try:
        pages = db.get_all_pages(limit, offset)
        return pages
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve pages: {str(e)}")


@app.get("/pages/{page_id}", response_model=PageResponse)
async def get_page(page_id: int):
    """Get a specific page by ID."""
    page = db.get_page_by_id(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return page


@app.delete("/pages/{page_id}", response_model=dict)
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


@app.get("/stats", response_model=dict)
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
