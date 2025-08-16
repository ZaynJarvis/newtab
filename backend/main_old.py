"""Local Web Memory Backend Service - FastAPI with SQLite FTS5 and vector search."""

import asyncio
import os
import sys
import time
import signal
import atexit
from datetime import datetime
from typing import List, Optional, Dict, Tuple

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models import (
    PageCreate, PageResponse, SearchRequest, UnifiedSearchResponse,
    HealthResponse, IndexResponse, VisitTrackingRequest, FrequencyAnalyticsResponse,
    QueryCacheStatsResponse, CachedQueryResponse
)
from database import Database
from vector_store import VectorStore
from api_client import ArkAPIClient
from src.core.config import settings

# Initialize configuration
try:
    config = settings
    print(f"✅ Configuration loaded successfully")
    print(f"🔑 API token configured: {config.ark_api_token[:8]}...")
except Exception as e:
    print(f"❌ ERROR: Failed to load configuration: {e}")
    print("Please ensure ARK_API_TOKEN is set in environment or .env file")
    print("Example: export ARK_API_TOKEN=\"your-api-token-here\"")
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

# Initialize components using configuration
db = Database()
vector_store = VectorStore(dimension=config.vector_dimension)
ark_client = None

# Initialize Ark API client using configuration
try:
    ark_client = ArkAPIClient(config)
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
            # Wrap health check with timeout to prevent startup hangs
            health = await asyncio.wait_for(ark_client.health_check(), timeout=10.0)
            print(f"🔗 API Health: {health['status']}")
        except asyncio.TimeoutError:
            print("❌ API health check timed out after 10s")
        except Exception as e:
            print(f"⚠️  API health check failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    print("🛑 Shutting down Local Web Memory Backend...")
    
    # Save query embedding cache before shutdown
    if ark_client:
        try:
            success = ark_client.query_cache.force_save()
            if success:
                stats = ark_client.get_cache_stats()
                print(f"💾 Query cache saved: {stats['size']} queries, {stats['hits']} hits")
            else:
                print("⚠️  Failed to save query cache")
        except Exception as e:
            print(f"❌ Error saving query cache: {e}")
    
    print("✅ Shutdown complete")


def save_cache_on_exit():
    """Fallback function to save cache on unexpected shutdown."""
    if ark_client:
        try:
            success = ark_client.query_cache.force_save()
            print(f"💾 Emergency cache save: {'✅ Success' if success else '❌ Failed'}")
        except Exception as e:
            print(f"❌ Emergency cache save failed: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    save_cache_on_exit()
    sys.exit(0)


# Register signal handlers and exit handlers
signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
atexit.register(save_cache_on_exit)             # Python exit


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
        # Check if URL needs re-indexing
        needs_reindex, existing_id = db.check_needs_reindex(page.url)
        
        if existing_id and not needs_reindex:
            # URL exists and doesn't need re-indexing, just update visit count
            db.update_visit_metrics(existing_id)
            
            return IndexResponse(
                id=existing_id,
                status="already_indexed",
                message="Page already indexed recently. Visit count updated.",
                processing_time=round((time.time() - start_time) * 1000, 2)
            )
        
        # Insert or update page
        page_id = db.insert_page(page)
        
        # Update index time
        db.update_page_index_time(page_id)
        
        # Schedule AI processing in background
        background_tasks.add_task(process_page_ai, page_id, page)
        
        processing_time = time.time() - start_time
        
        return IndexResponse(
            id=page_id,
            status="indexed" if not existing_id else "re-indexed",
            message="Page indexed successfully. AI processing in progress.",
            processing_time=round(processing_time * 1000, 2)  # Convert to milliseconds
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")












@app.post("/track-visit", response_model=dict, tags=["tracking"])
async def track_visit(visit_data: VisitTrackingRequest):
    """Track a page visit and update frequency metrics."""
    try:
        # Find existing page or create placeholder
        page_id = db.find_or_create_page_for_tracking(visit_data.url)
        
        if not page_id:
            raise HTTPException(status_code=404, detail="Could not find or create page for tracking")
        
        # Update visit metrics (includes count suppression check)
        success = db.update_visit_metrics(page_id, suppress_counts=True)
        
        if success:
            # Check if eviction is needed (every 100th visit to avoid overhead)
            import random
            if random.randint(1, 100) == 1:  # 1% chance to check eviction
                eviction_result = db.check_and_evict_pages()
                if eviction_result['evicted_count'] > 0:
                    print(f"🧹 Auto-evicted {eviction_result['evicted_count']} pages during visit tracking")
            
            return {
                "status": "success",
                "page_id": page_id,
                "message": "Visit tracked successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to track visit")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visit tracking failed: {str(e)}")


@app.get("/analytics/frequency", response_model=FrequencyAnalyticsResponse, tags=["analytics"])
async def get_frequency_analytics(days: int = 30):
    """Get frequency and visit analytics."""
    try:
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with db.get_connection() as conn:
            # Total visits
            total_visits = conn.execute("""
                SELECT SUM(visit_count) as total
                FROM pages
                WHERE last_visited >= ?
            """, (cutoff_date,)).fetchone()['total'] or 0
            
            # Unique pages visited
            unique_pages = conn.execute("""
                SELECT COUNT(*) as count
                FROM pages
                WHERE last_visited >= ? AND visit_count > 0
            """, (cutoff_date,)).fetchone()['count']
            
            # Most visited pages
            most_visited = conn.execute("""
                SELECT url, title, visit_count, last_visited
                FROM pages
                WHERE last_visited >= ? AND visit_count > 0
                ORDER BY visit_count DESC
                LIMIT 10
            """, (cutoff_date,)).fetchall()
            
            # Recent activity
            recent_activity = conn.execute("""
                SELECT url, title, last_visited, visit_count
                FROM pages
                WHERE last_visited >= ?
                ORDER BY last_visited DESC
                LIMIT 20
            """, (cutoff_date,)).fetchall()
            
            return FrequencyAnalyticsResponse(
                total_visits=total_visits,
                unique_pages=unique_pages,
                avg_visits_per_page=total_visits / max(unique_pages, 1),
                most_visited_pages=[dict(row) for row in most_visited],
                recent_activity=[dict(row) for row in recent_activity],
                access_patterns={
                    "period_days": days,
                    "daily_average": total_visits / days if days > 0 else 0
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")


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
            """
            Get vector search results with 3-step fallback strategy:
            1. Use exact cached embedding for query
            2. If not cached, call API and cache result
            3. If API fails, use keyword search top-1 result's embedding for similarity search
            """
            if not ark_client:
                return []
            
            try:
                # Step 1 & 2: Generate embedding for query (cache-aware)
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
                
                # Step 3: Fallback to keyword search top-1 result's embedding for similarity
                try:
                    print(f"Attempting fallback: using keyword search top result's embedding")
                    keyword_fallback_results, _ = db.search_keyword(q, 1)
                    
                    if keyword_fallback_results and len(keyword_fallback_results) > 0:
                        top_result = keyword_fallback_results[0]
                        
                        # Get the stored embedding for the top keyword result
                        stored_embedding = db.get_page_embedding(top_result.id)
                        
                        if stored_embedding:
                            print(f"Using stored embedding from top keyword result: {top_result.title[:50]}...")
                            
                            # Use top result's embedding for vector similarity search
                            fallback_vector_results = vector_store.search(
                                stored_embedding,
                                MAX_RESULTS * 2,
                                MIN_SIMILARITY,
                                enable_clustering=ENABLE_SMART_CUTOFF,
                                similarity_drop_threshold=SIMILARITY_DROP_THRESHOLD
                            )
                            
                            # Format fallback results
                            formatted_fallback = []
                            for page_data, similarity in fallback_vector_results:
                                result_dict = page_data.dict()
                                result_dict['vector_similarity'] = round(similarity, 4)
                                # Mark as fallback result
                                result_dict['fallback_source'] = 'keyword_top_result_embedding'
                                formatted_fallback.append(result_dict)
                            
                            return formatted_fallback
                        else:
                            print(f"No stored embedding found for top keyword result")
                    else:
                        print(f"No keyword results found for fallback")
                
                except Exception as fallback_error:
                    print(f"Fallback strategy also failed: {fallback_error}")
                
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
        
        # Apply ARC-based re-ranking with visit count
        final_results = list(url_to_result.values())
        
        # First pass: calculate base final scores without frequency boost
        for result in final_results:
            result['final_score'] = result.get('relevance_score', 0.0)
        
        # Find max score for frequency boost range calculation
        if final_results:
            max_score = max(result['final_score'] for result in final_results)
            frequency_threshold = max_score - 0.05  # Apply boost only within 0.05 of max
        else:
            max_score = 0.0
            frequency_threshold = 0.0
        
        # Second pass: apply frequency boost only to top-scoring results
        for result in final_results:
            # Get frequency metrics from result (already included from database)
            visit_count = result.get('visit_count', 0)
            arc_score = result.get('arc_score', 0.0)
            relevance_score = result.get('relevance_score', 0.0)
            
            # Apply frequency boost only to results within 0.05 of max score
            if result['final_score'] >= frequency_threshold and visit_count > 0:
                # Normalize visit count for boosting (max boost of 20%)
                frequency_boost = min(visit_count / 50.0, 0.2)  # Cap at 20% boost
                arc_boost = arc_score * 0.1  # ARC score contributes up to 10% boost
                
                # Apply frequency boost to top results only
                result['final_score'] = relevance_score + frequency_boost + arc_boost
                result['frequency_boost'] = frequency_boost
                result['arc_boost'] = arc_boost
            else:
                # No frequency boost for lower scoring results
                result['frequency_boost'] = 0.0
                result['arc_boost'] = 0.0
        
        # Sort by combined final score and limit to MAX_RESULTS
        final_results.sort(key=lambda x: x['final_score'], reverse=True)
        final_results = final_results[:MAX_RESULTS]
        
        # Clean up results for response and prepare metadata for frontend
        for result in final_results:
            # Keep the final relevance score
            result['relevance_score'] = round(result.get('final_score', 0.0), 4)
            
            # Preserve scoring metadata for hover hints
            result['metadata'] = {
                'vector_score': round(result.get('vector_score', 0.0), 4),
                'keyword_score': round(result.get('keyword_score', 0.0), 4),
                'access_count': result.get('visit_count', 0),
                'final_score': round(result.get('final_score', 0.0), 4)
            }
            
            # Remove internal scoring fields (now preserved in metadata)
            result.pop('keyword_score', None)
            result.pop('vector_score', None)
            result.pop('vector_similarity', None)
            result.pop('final_score', None)
            result.pop('frequency_boost', None)
            result.pop('arc_boost', None)
        
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


@app.post("/eviction/run", response_model=dict, tags=["eviction"])
async def run_eviction():
    """Manually trigger eviction process."""
    try:
        result = db.check_and_evict_pages()
        return {
            "status": "completed",
            "evicted_count": result["evicted_count"],
            "total_pages": result["total_pages"],
            "candidates_found": result["candidates_found"],
            "message": f"Evicted {result['evicted_count']} pages"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Eviction failed: {str(e)}")


@app.get("/eviction/preview", response_model=dict, tags=["eviction"])
async def preview_eviction_candidates(count: int = 10):
    """Preview pages that would be evicted."""
    try:
        candidates = db.get_eviction_candidates_preview(count)
        return {
            "candidates": candidates,
            "count": len(candidates),
            "message": f"Found {len(candidates)} eviction candidates"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@app.get("/eviction/stats", response_model=dict, tags=["eviction"])
async def get_eviction_stats():
    """Get eviction statistics and distribution analysis."""
    try:
        stats = db.get_eviction_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")


@app.get("/cache/query/stats", response_model=QueryCacheStatsResponse, tags=["cache"])
async def get_query_cache_stats():
    """Get query embedding cache statistics."""
    try:
        if not ark_client:
            raise HTTPException(status_code=503, detail="API client not available")
        
        stats = ark_client.get_cache_stats()
        return QueryCacheStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache stats failed: {str(e)}")


@app.get("/cache/query/top", response_model=List[CachedQueryResponse], tags=["cache"])
async def get_top_cached_queries(limit: int = 10):
    """Get most frequently cached queries."""
    try:
        if not ark_client:
            raise HTTPException(status_code=503, detail="API client not available")
        
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        top_queries = ark_client.get_top_cached_queries(limit)
        return [CachedQueryResponse(**query) for query in top_queries]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Top queries failed: {str(e)}")


@app.post("/cache/query/clear", response_model=dict, tags=["cache"])
async def clear_query_cache():
    """Clear all cached query embeddings."""
    try:
        if not ark_client:
            raise HTTPException(status_code=503, detail="API client not available")
        
        success = ark_client.clear_cache()
        if success:
            return {
                "status": "success",
                "message": "Query embedding cache cleared successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to clear cache")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")


@app.post("/cache/query/cleanup", response_model=dict, tags=["cache"])
async def cleanup_query_cache():
    """Clean up expired query cache entries."""
    try:
        if not ark_client:
            raise HTTPException(status_code=503, detail="API client not available")
        
        removed_count = ark_client.cleanup_cache()
        return {
            "status": "success",
            "removed_count": removed_count,
            "message": f"Cleaned up {removed_count} expired cache entries"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache cleanup failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Local Web Memory Backend Server...")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
        log_level=config.log_level
    )
