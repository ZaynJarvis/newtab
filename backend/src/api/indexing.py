"""Page indexing and content management endpoints."""

import time
from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from src.core.models import PageCreate, PageResponse, IndexResponse, ProbeResponse
from src.core.logging import get_logger


router = APIRouter()
logger = get_logger(__name__)

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


async def process_page_ai(page_id: int, page: PageCreate):
    """Background task to process page with AI services."""
    if not ark_client:
        logger.info(
            "Skipping AI processing - no API client",
            extra={
                "page_id": page_id,
                "event": "ai_processing_skipped"
            }
        )
        return
    
    try:
        # Generate keywords, description, and improved title
        ai_data = await ark_client.generate_keywords_and_description(page.title, page.content)
        
        # Use improved title if available, fallback to original title
        final_title = ai_data.get('improved_title', page.title)
        
        # Generate vector embedding using the final title
        embedding_text = f"{final_title} {ai_data['description']} {page.content[:1000]}"
        vector_embedding = await ark_client.generate_embedding(embedding_text)
        
        # Update database with AI-generated data including improved title
        import json
        vector_json = json.dumps(vector_embedding) if vector_embedding else None
        with db.get_connection() as conn:
            conn.execute("""
                UPDATE pages 
                SET title = ?, description = ?, keywords = ?, vector_embedding = ?
                WHERE id = ?
            """, (final_title, ai_data['description'], ai_data['keywords'], 
                  vector_json, page_id))
            conn.commit()
        
        # Update vector store
        updated_page = db.get_page_by_id(page_id)
        if updated_page and vector_embedding:
            vector_store.add_vector(page_id, vector_embedding, updated_page)
        
        logger.info(
            "AI processing completed successfully",
            extra={
                "page_id": page_id,
                "final_title": final_title,
                "has_embedding": bool(vector_embedding),
                "event": "ai_processing_completed"
            }
        )
    
    except Exception as e:
        logger.error(
            "AI processing failed",
            extra={
                "page_id": page_id,
                "error": str(e),
                "event": "ai_processing_failed"
            },
            exc_info=True
        )


@router.post("/index", response_model=IndexResponse)
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


@router.get("/pages", response_model=List[PageResponse])
async def get_pages(limit: int = 100, offset: int = 0):
    """Get all pages with pagination."""
    if limit > 1000:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 1000")
    
    try:
        pages = db.get_all_pages(limit, offset)
        return pages
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve pages: {str(e)}")


@router.get("/pages/{page_id}", response_model=PageResponse)
async def get_page(page_id: int):
    """Get a specific page by ID."""
    page = db.get_page_by_id(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return page


@router.get("/probe", response_model=ProbeResponse)
async def probe_page(url: str):
    """Probe if a page is already indexed without full processing."""
    try:
        # Check if URL exists and needs re-indexing
        needs_reindex, existing_id = db.check_needs_reindex(url)
        
        if existing_id:
            # Page exists, update visit metrics
            db.update_visit_metrics(existing_id)
            
            # Get last updated time
            page = db.get_page_by_id(existing_id)
            last_updated = page.last_updated_at if page else None
            
            return ProbeResponse(
                indexed=True,
                page_id=existing_id,
                last_updated=last_updated,
                needs_reindex=needs_reindex
            )
        else:
            # Page doesn't exist
            return ProbeResponse(
                indexed=False,
                page_id=None,
                last_updated=None,
                needs_reindex=False
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Probe failed: {str(e)}")


@router.delete("/pages/{page_id}", response_model=dict)
async def delete_page(page_id: int):
    """Delete a specific page by ID."""
    try:
        logger.info(f"🗑️ Delete request received for page ID: {page_id}")
        
        # Get page info before deletion for logging
        page_info = db.get_page_by_id(page_id)
        if page_info:
            logger.info(f"🗑️ Deleting page: {page_info.title} - {page_info.url}")
        
        # Remove from vector store
        vector_store.remove_vector(page_id)
        logger.info(f"🗑️ Removed page {page_id} from vector store")
        
        # Remove from database
        deleted = db.delete_page(page_id)
        
        if not deleted:
            logger.warning(f"❌ Page {page_id} not found in database")
            raise HTTPException(status_code=404, detail="Page not found")
        
        logger.info(f"✅ Page {page_id} deleted successfully from database")
        
        return {
            "status": "deleted",
            "page_id": page_id,
            "message": "Page deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete page {page_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete page: {str(e)}")