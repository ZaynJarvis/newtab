"""Monitoring and metrics endpoints for Local Web Memory Backend."""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import psutil
import sys
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.core.logging import get_logger, log_api_call


logger = get_logger(__name__)

# Global variables for dependency injection
_db = None
_ark_client = None
_vector_store = None

# Metrics storage
_metrics = {
    "requests": {
        "total": 0,
        "by_method": {},
        "by_status": {},
        "response_times": []
    },
    "api_calls": {
        "total": 0,
        "successful": 0,
        "failed": 0,
        "response_times": []
    },
    "database": {
        "operations": 0,
        "queries": 0,
        "response_times": []
    },
    "cache": {
        "hits": 0,
        "misses": 0,
        "operations": 0
    },
    "errors": {
        "total": 0,
        "by_type": {}
    }
}

router = APIRouter()


def inject_dependencies(db, ark_client, vector_store):
    """Inject database, API client and vector store dependencies."""
    global _db, _ark_client, _vector_store
    _db = db
    _ark_client = ark_client
    _vector_store = vector_store


class SystemMetrics(BaseModel):
    """System metrics model."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    uptime_seconds: float
    python_version: str
    process_id: int


class ApplicationMetrics(BaseModel):
    """Application metrics model."""
    requests_total: int
    requests_by_method: Dict[str, int]
    requests_by_status: Dict[str, int]
    avg_response_time_ms: float
    api_calls_total: int
    api_calls_successful: int
    api_calls_failed: int
    api_success_rate: float
    database_operations: int
    cache_hits: int
    cache_misses: int
    cache_hit_rate: float
    errors_total: int
    vector_store_size: int
    database_size_mb: Optional[float]


class HealthStatus(BaseModel):
    """Health status model."""
    status: str
    timestamp: str
    uptime_seconds: float
    checks: Dict[str, Dict[str, Any]]


def get_system_metrics() -> SystemMetrics:
    """Get system-level metrics."""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_used_mb = (memory.total - memory.available) / 1024 / 1024
        memory_available_mb = memory.available / 1024 / 1024
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_free_gb = disk.free / 1024 / 1024 / 1024
        disk_usage_percent = (disk.used / disk.total) * 100
        
        # Process info
        process = psutil.Process()
        uptime_seconds = time.time() - process.create_time()
        
        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory_used_mb,
            memory_available_mb=memory_available_mb,
            disk_usage_percent=disk_usage_percent,
            disk_free_gb=disk_free_gb,
            uptime_seconds=uptime_seconds,
            python_version=sys.version,
            process_id=os.getpid()
        )
    except Exception as e:
        logger.error("Failed to get system metrics", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get system metrics")


def get_application_metrics() -> ApplicationMetrics:
    """Get application-level metrics."""
    try:
        # Calculate averages
        avg_response_time = 0
        if _metrics["requests"]["response_times"]:
            avg_response_time = sum(_metrics["requests"]["response_times"]) / len(_metrics["requests"]["response_times"])
        
        # API success rate
        api_total = _metrics["api_calls"]["total"]
        api_success_rate = 0
        if api_total > 0:
            api_success_rate = (_metrics["api_calls"]["successful"] / api_total) * 100
        
        # Cache hit rate
        cache_total = _metrics["cache"]["hits"] + _metrics["cache"]["misses"]
        cache_hit_rate = 0
        if cache_total > 0:
            cache_hit_rate = (_metrics["cache"]["hits"] / cache_total) * 100
        
        # Vector store size
        vector_store_size = 0
        if _vector_store and hasattr(_vector_store, '_vectors'):
            vector_store_size = len(_vector_store._vectors)
        
        # Database size
        database_size_mb = None
        if _db and hasattr(_db, 'db_file') and _db.db_file != ":memory:":
            try:
                db_path = Path(_db.db_file)
                if db_path.exists():
                    database_size_mb = db_path.stat().st_size / 1024 / 1024
            except Exception:
                pass
        
        return ApplicationMetrics(
            requests_total=_metrics["requests"]["total"],
            requests_by_method=_metrics["requests"]["by_method"],
            requests_by_status=_metrics["requests"]["by_status"],
            avg_response_time_ms=avg_response_time,
            api_calls_total=_metrics["api_calls"]["total"],
            api_calls_successful=_metrics["api_calls"]["successful"],
            api_calls_failed=_metrics["api_calls"]["failed"],
            api_success_rate=api_success_rate,
            database_operations=_metrics["database"]["operations"],
            cache_hits=_metrics["cache"]["hits"],
            cache_misses=_metrics["cache"]["misses"],
            cache_hit_rate=cache_hit_rate,
            errors_total=_metrics["errors"]["total"],
            vector_store_size=vector_store_size,
            database_size_mb=database_size_mb
        )
    except Exception as e:
        logger.error("Failed to get application metrics", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get application metrics")


async def check_database_health() -> Dict[str, Any]:
    """Check database health."""
    try:
        start_time = time.time()
        
        # Simple query to test database
        pages = _db.get_all_pages(limit=1)
        
        response_time = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "response_time_ms": response_time,
            "accessible": True
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "accessible": False
        }


async def check_api_client_health() -> Dict[str, Any]:
    """Check API client health."""
    if not _ark_client:
        return {
            "status": "unavailable",
            "message": "API client not configured"
        }
    
    try:
        start_time = time.time()
        health = await _ark_client.health_check()
        response_time = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "response_time_ms": response_time,
            "api_status": health.get("status", "unknown")
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_vector_store_health() -> Dict[str, Any]:
    """Check vector store health."""
    try:
        vector_count = 0
        if _vector_store and hasattr(_vector_store, '_vectors'):
            vector_count = len(_vector_store._vectors)
        
        return {
            "status": "healthy",
            "vector_count": vector_count,
            "accessible": True
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "accessible": False
        }


def record_request_metric(method: str, status_code: int, response_time_ms: float):
    """Record request metrics."""
    _metrics["requests"]["total"] += 1
    _metrics["requests"]["by_method"][method] = _metrics["requests"]["by_method"].get(method, 0) + 1
    _metrics["requests"]["by_status"][str(status_code)] = _metrics["requests"]["by_status"].get(str(status_code), 0) + 1
    _metrics["requests"]["response_times"].append(response_time_ms)
    
    # Keep only last 1000 response times
    if len(_metrics["requests"]["response_times"]) > 1000:
        _metrics["requests"]["response_times"] = _metrics["requests"]["response_times"][-1000:]


def record_api_call_metric(success: bool, response_time_ms: float):
    """Record API call metrics."""
    _metrics["api_calls"]["total"] += 1
    if success:
        _metrics["api_calls"]["successful"] += 1
    else:
        _metrics["api_calls"]["failed"] += 1
    
    _metrics["api_calls"]["response_times"].append(response_time_ms)
    
    # Keep only last 1000 response times
    if len(_metrics["api_calls"]["response_times"]) > 1000:
        _metrics["api_calls"]["response_times"] = _metrics["api_calls"]["response_times"][-1000:]


def record_database_metric(response_time_ms: float):
    """Record database operation metrics."""
    _metrics["database"]["operations"] += 1
    _metrics["database"]["response_times"].append(response_time_ms)
    
    # Keep only last 1000 response times
    if len(_metrics["database"]["response_times"]) > 1000:
        _metrics["database"]["response_times"] = _metrics["database"]["response_times"][-1000:]


def record_cache_metric(hit: bool):
    """Record cache metrics."""
    _metrics["cache"]["operations"] += 1
    if hit:
        _metrics["cache"]["hits"] += 1
    else:
        _metrics["cache"]["misses"] += 1


def record_error_metric(error_type: str):
    """Record error metrics."""
    _metrics["errors"]["total"] += 1
    _metrics["errors"]["by_type"][error_type] = _metrics["errors"]["by_type"].get(error_type, 0) + 1


@router.get("/metrics/system", response_model=SystemMetrics)
async def get_system_metrics_endpoint():
    """Get system-level metrics."""
    logger.info("System metrics requested")
    return get_system_metrics()


@router.get("/metrics/application", response_model=ApplicationMetrics)
async def get_application_metrics_endpoint():
    """Get application-level metrics."""
    logger.info("Application metrics requested")
    return get_application_metrics()


@router.get("/metrics", response_model=Dict[str, Any])
async def get_all_metrics():
    """Get all metrics."""
    logger.info("All metrics requested")
    
    try:
        system_metrics = get_system_metrics()
        app_metrics = get_application_metrics()
        
        return {
            "system": system_metrics.dict(),
            "application": app_metrics.dict(),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error("Failed to get metrics", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get metrics")


@router.get("/health/detailed", response_model=HealthStatus)
async def get_detailed_health():
    """Get detailed health status with all component checks."""
    logger.info("Detailed health check requested")
    
    try:
        # Get uptime
        process = psutil.Process()
        uptime_seconds = time.time() - process.create_time()
        
        # Run health checks
        db_health = await check_database_health()
        api_health = await check_api_client_health()
        vector_health = await check_vector_store_health()
        
        # Determine overall status
        checks = {
            "database": db_health,
            "api_client": api_health,
            "vector_store": vector_health
        }
        
        # Overall status is healthy if all critical components are healthy
        overall_status = "healthy"
        if (db_health.get("status") != "healthy" or 
            vector_health.get("status") != "healthy"):
            overall_status = "unhealthy"
        elif api_health.get("status") == "unhealthy":
            overall_status = "degraded"  # API client is optional
        
        return HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            uptime_seconds=uptime_seconds,
            checks=checks
        )
    except Exception as e:
        logger.error("Failed to get detailed health", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get health status")


@router.get("/health/live")
async def liveness_probe():
    """Kubernetes/Docker liveness probe endpoint."""
    try:
        # Basic liveness check - just verify the service is responding
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error("Liveness probe failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Liveness probe failed")


@router.get("/health/ready")
async def readiness_probe():
    """Kubernetes/Docker readiness probe endpoint."""
    try:
        # Check if the service is ready to handle requests
        db_health = await check_database_health()
        vector_health = await check_vector_store_health()
        
        if (db_health.get("status") == "healthy" and 
            vector_health.get("status") == "healthy"):
            return {
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        else:
            raise HTTPException(status_code=503, detail="Service not ready")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Readiness probe failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=503, detail="Readiness probe failed")


@router.post("/metrics/reset")
async def reset_metrics():
    """Reset all metrics (useful for testing)."""
    logger.warning("Metrics reset requested")
    
    global _metrics
    _metrics = {
        "requests": {
            "total": 0,
            "by_method": {},
            "by_status": {},
            "response_times": []
        },
        "api_calls": {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "response_times": []
        },
        "database": {
            "operations": 0,
            "queries": 0,
            "response_times": []
        },
        "cache": {
            "hits": 0,
            "misses": 0,
            "operations": 0
        },
        "errors": {
            "total": 0,
            "by_type": {}
        }
    }
    
    return {"success": True, "message": "Metrics reset successfully"}


@router.get("/status")
async def get_service_status():
    """Get comprehensive service status."""
    logger.info("Service status requested")
    
    try:
        system_metrics = get_system_metrics()
        app_metrics = get_application_metrics()
        health_status = await get_detailed_health()
        
        return {
            "service": "Local Web Memory Backend",
            "version": "2.0.0",
            "status": health_status.status,
            "uptime_seconds": health_status.uptime_seconds,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": {
                "requests_total": app_metrics.requests_total,
                "avg_response_time_ms": app_metrics.avg_response_time_ms,
                "api_success_rate": app_metrics.api_success_rate,
                "cache_hit_rate": app_metrics.cache_hit_rate,
                "vector_store_size": app_metrics.vector_store_size,
                "errors_total": app_metrics.errors_total
            },
            "system": {
                "cpu_percent": system_metrics.cpu_percent,
                "memory_percent": system_metrics.memory_percent,
                "disk_usage_percent": system_metrics.disk_usage_percent
            },
            "components": health_status.checks
        }
    except Exception as e:
        logger.error("Failed to get service status", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get service status")


# Export metric recording functions for use in other modules
__all__ = [
    'record_request_metric',
    'record_api_call_metric', 
    'record_database_metric',
    'record_cache_metric',
    'record_error_metric',
    'router'
]