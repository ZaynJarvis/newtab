"""Analytics and visit tracking endpoints."""

from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from src.core.models import VisitTrackingRequest, FrequencyAnalyticsResponse
from src.core.logging import get_logger


router = APIRouter()
logger = get_logger(__name__)

# Import dependencies - will be injected at runtime
db = None


def inject_dependencies(database, api_client=None, vector_storage=None):
    """Inject dependencies at startup."""
    global db
    db = database


@router.post("/track-visit", response_model=dict)
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
                    logger.info(
                        "Auto-evicted pages during visit tracking",
                        extra={
                            "evicted_count": eviction_result['evicted_count'],
                            "event": "auto_eviction"
                        }
                    )
            
            return {
                "status": "success",
                "page_id": page_id,
                "message": "Visit tracked successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to track visit")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visit tracking failed: {str(e)}")


@router.get("/analytics/frequency", response_model=FrequencyAnalyticsResponse)
async def get_frequency_analytics(days: int = 30):
    """Get frequency and visit analytics."""
    try:
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