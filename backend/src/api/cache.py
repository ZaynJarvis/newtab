"""Query cache management endpoints."""

from typing import List
from fastapi import APIRouter, HTTPException
from src.core.models import QueryCacheStatsResponse, CachedQueryResponse


router = APIRouter()

# Import dependencies - will be injected at runtime
ark_client = None


def inject_dependencies(database=None, api_client=None, vector_storage=None):
    """Inject dependencies at startup."""
    global ark_client
    ark_client = api_client


@router.get("/cache/query/stats", response_model=QueryCacheStatsResponse)
async def get_query_cache_stats():
    """Get query embedding cache statistics."""
    try:
        if not ark_client:
            raise HTTPException(status_code=503, detail="API client not available")
        
        stats = ark_client.get_cache_stats()
        return QueryCacheStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache stats failed: {str(e)}")


@router.get("/cache/query/top", response_model=List[CachedQueryResponse])
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


@router.post("/cache/query/clear", response_model=dict)
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


@router.post("/cache/query/cleanup", response_model=dict)
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