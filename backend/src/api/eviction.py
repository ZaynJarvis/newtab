"""Page eviction and memory management endpoints."""

from fastapi import APIRouter, HTTPException


router = APIRouter()

# Import dependencies - will be injected at runtime
db = None


def inject_dependencies(database, api_client=None, vector_storage=None):
    """Inject dependencies at startup."""
    global db
    db = database


@router.post("/eviction/run", response_model=dict)
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


@router.get("/eviction/preview", response_model=dict)
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


@router.get("/eviction/stats", response_model=dict)
async def get_eviction_stats():
    """Get eviction statistics and distribution analysis."""
    try:
        stats = db.get_eviction_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")