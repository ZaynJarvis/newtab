"""Health check and system status endpoints."""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from src.core.models import HealthResponse


router = APIRouter()

# Import dependencies - will be injected at runtime
db = None
ark_client = None
vector_store = None


def inject_dependencies(database, api_client, vector_storage):
    """Inject dependencies at startup."""
    global db, ark_client, vector_store
    db = database
    ark_client = api_client
    vector_store = vector_storage


@router.get("/health", response_model=HealthResponse)
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


@router.get("/stats", response_model=dict)
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