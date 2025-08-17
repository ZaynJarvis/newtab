"""Main application entry point for New Tab Backend Service."""

import sys
import signal
import atexit
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
import time
import uuid

from src.core.config import settings
from src.core.logging import get_logger, log_request_start, log_request_end
from src.core.exceptions import (
    LocalWebMemoryException,
    local_web_memory_exception_handler,
    general_exception_handler,
    http_exception_handler_with_logging,
    validation_exception_handler
)
from src.services.api_client import ArkAPIClient
from src.services.multi_provider_client import MultiProviderAPIClient
from src.services.provider_factory import ProviderFactory
from src.core.database import Database
from src.services.vector_store import VectorStore
from src.api.health import router as health_router
from src.api.indexing import router as indexing_router
from src.api.search import router as search_router
from src.api.analytics import router as analytics_router
from src.api.eviction import router as eviction_router
from src.api.cache import router as cache_router
from src.api.monitoring import router as monitoring_router


# Initialize logging
logger = get_logger(__name__)

# Initialize configuration
try:
    config = settings
    logger.info("Configuration loaded successfully", extra={
        "llm_api_token_prefix": config.llm_api_token[:8] + "...",
        "embedding_api_token_prefix": config.embedding_api_token[:8] + "...",
        "llm_provider": config.llm_provider,
        "embedding_provider": config.embedding_provider,
        "host": config.host,
        "port": config.port,
        "log_level": config.log_level
    })
except Exception as e:
    logger.critical("Failed to load configuration", extra={"error": str(e)}, exc_info=True)
    logger.critical("Configuration setup required", extra={
        "required_env_var": "API_TOKEN",
        "setup_example": "export API_TOKEN=\"your-api-token-here\"",
        "event": "configuration_setup_required"
    })
    sys.exit(1)

# Initialize FastAPI app
app = FastAPI(
    title="New Tab Backend API",
    description="""
    ## 🔍 New Tab Backend Service

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
        "name": "New Tab Team",
        "url": "https://github.com/newtab/backend",
        "email": "support@newtab.dev"
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
        },
        {
            "name": "analytics",
            "description": "Frequency and visit analytics"
        },
        {
            "name": "eviction",
            "description": "Page eviction and memory management"
        },
        {
            "name": "cache",
            "description": "Query cache management"
        },
        {
            "name": "monitoring",
            "description": "Service monitoring and metrics"
        }
    ]
)

# Add request logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Middleware for request/response logging."""
    # Generate request ID
    request_id = str(uuid.uuid4())
    
    # Get client IP
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    elif "x-real-ip" in request.headers:
        client_ip = request.headers["x-real-ip"]
    
    # Start request logging
    request_logger = log_request_start(
        method=request.method,
        url=str(request.url),
        client_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
        request_id=request_id
    )
    
    # Add request ID to state for access in endpoints
    request.state.request_id = request_id
    request.state.logger = request_logger
    
    # Process request
    start_time = time.time()
    try:
        response = await call_next(request)
        
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Log response
        log_request_end(
            logger=request_logger,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            response_size=None  # FastAPI doesn't provide easy access to response size
        )
        
        # Record metrics
        from src.api.monitoring import record_request_metric
        record_request_metric(request.method, response.status_code, response_time_ms)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    except Exception as exc:
        response_time_ms = (time.time() - start_time) * 1000
        request_logger.error(
            f"Request failed with exception: {str(exc)}",
            extra={
                "event": "request_error",
                "response_time_ms": response_time_ms,
                "exception": str(exc)
            },
            exc_info=True
        )
        raise

# Add CORS middleware for Chrome extension access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
db = Database(config.database_file)
vector_store = VectorStore(dimension=config.vector_dimension, max_vectors=config.max_vectors)
ark_client = None

# Validate provider configuration
is_valid, error_msg = ProviderFactory.validate_provider_compatibility(config)
if not is_valid:
    logger.critical("Invalid provider configuration", extra={
        "error": error_msg,
        "llm_provider": config.llm_provider,
        "embedding_provider": config.embedding_provider,
        "event": "invalid_provider_config"
    })
    sys.exit(1)

# Initialize Multi-Provider API client
try:
    ark_client = MultiProviderAPIClient(config)
    logger.info("Multi-provider API client initialized successfully", extra={
        "llm_provider": config.llm_provider,
        "embedding_provider": config.embedding_provider,
        "event": "api_client_initialized"
    })
except Exception as e:
    logger.warning("Multi-provider API client initialization failed, running in mock mode", extra={
        "error": str(e),
        "mode": "mock",
        "event": "api_client_mock_mode"
    }, exc_info=True)


# Inject dependencies into API routers
from src.api import health, indexing, search, analytics, eviction, cache, monitoring

health.inject_dependencies(db, ark_client, vector_store)
indexing.inject_dependencies(db, ark_client, vector_store)
search.inject_dependencies(db, ark_client, vector_store)
analytics.inject_dependencies(db, ark_client, vector_store)
eviction.inject_dependencies(db, ark_client, vector_store)
cache.inject_dependencies(db, ark_client, vector_store)
monitoring.inject_dependencies(db, ark_client, vector_store)

# Include API routers
app.include_router(health_router, tags=["health"])
app.include_router(indexing_router, tags=["indexing"])
app.include_router(search_router, tags=["search"])
app.include_router(analytics_router, tags=["analytics"])
app.include_router(eviction_router, tags=["eviction"])
app.include_router(cache_router, tags=["cache"])
app.include_router(monitoring_router, tags=["monitoring"])

# Register exception handlers
app.add_exception_handler(LocalWebMemoryException, local_web_memory_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler_with_logging)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    logger.info("Starting New Tab Backend")
    
    # Load existing vectors into memory
    try:
        vectors_data = db.get_all_vectors()
        for page_id, vector in vectors_data:
            page_data = db.get_page_by_id(page_id)
            if page_data:
                vector_store.add_vector(page_id, vector, page_data)
        
        logger.info("Loaded vectors into memory", extra={
            "vector_count": len(vectors_data),
            "event": "startup_vectors_loaded"
        })
    except Exception as e:
        logger.error("Error loading vectors", extra={"error": str(e)}, exc_info=True)
    
    # Test API connection if available
    if ark_client:
        try:
            import asyncio
            # Wrap health check with timeout to prevent startup hangs
            health = await asyncio.wait_for(ark_client.health_check(), timeout=10.0)
            logger.info("API health check completed", extra={
                "api_status": health['status'],
                "event": "startup_api_health"
            })
        except asyncio.TimeoutError:
            logger.error("API health check timed out after 10s", extra={
                "timeout_seconds": 10,
                "event": "startup_api_timeout"
            })
        except Exception as e:
            logger.warning("API health check failed", extra={"error": str(e)}, exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down New Tab Backend")
    
    # Save query embedding cache before shutdown
    if ark_client:
        try:
            success = ark_client.query_cache.force_save()
            if success:
                stats = ark_client.get_cache_stats()
                logger.info("Query cache saved successfully", extra={
                    "cache_size": stats['size'],
                    "cache_hits": stats['hits'],
                    "event": "shutdown_cache_saved"
                })
            else:
                logger.warning("Failed to save query cache", extra={"event": "shutdown_cache_failed"})
        except Exception as e:
            logger.error("Error saving query cache", extra={"error": str(e)}, exc_info=True)
    
    logger.info("Shutdown complete", extra={"event": "shutdown_complete"})


def save_cache_on_exit():
    """Fallback function to save cache on unexpected shutdown."""
    if ark_client:
        try:
            success = ark_client.query_cache.force_save()
            logger.info("Emergency cache save completed", extra={
                "success": success,
                "event": "emergency_cache_save"
            })
        except Exception as e:
            logger.error("Emergency cache save failed", extra={"error": str(e)}, exc_info=True)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal", extra={
        "signal": signum,
        "event": "signal_received"
    })
    save_cache_on_exit()
    sys.exit(0)


# Register signal handlers and exit handlers
signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
atexit.register(save_cache_on_exit)             # Python exit


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with service information."""
    from datetime import datetime
    return {
        "service": "New Tab Backend",
        "version": "2.0.0",
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


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting New Tab Backend Server...")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    
    uvicorn.run(
        "src.main:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
        log_level=config.log_level
    )