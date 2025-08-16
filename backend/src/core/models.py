"""Data models for the New Tab backend service."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PageCreate(BaseModel):
    """Model for creating a new page entry."""
    url: str = Field(..., description="Full URL including query params")
    title: str = Field(..., description="Page title")
    content: str = Field(..., description="Extracted main content")
    favicon_url: Optional[str] = Field(None, description="URL to page favicon")


class PageResponse(BaseModel):
    """Model for page response data."""
    id: int
    url: str
    title: str
    description: str
    keywords: str
    content: str
    favicon_url: Optional[str]
    created_at: datetime
    vector_embedding: Optional[List[float]] = None
    
    # Frequency tracking fields
    visit_count: int = 0
    first_visited: Optional[datetime] = None
    last_visited: Optional[datetime] = None
    indexed_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
    access_frequency: float = 0.0
    recency_score: float = 0.0
    arc_score: float = 0.0


class SearchRequest(BaseModel):
    """Model for search requests."""
    query: str = Field(..., description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Number of results to return")


class UnifiedSearchResponse(BaseModel):
    """Model for unified search results with server-controlled ranking."""
    results: List[dict]  # PageResponse + relevance_score
    total_found: int
    query: str


class HealthResponse(BaseModel):
    """Model for health check response."""
    status: str
    timestamp: datetime
    database_connected: bool
    total_pages: int


class IndexResponse(BaseModel):
    """Model for indexing response."""
    id: int
    status: str
    message: str
    processing_time: float


class VisitTrackingRequest(BaseModel):
    """Model for visit tracking requests."""
    url: str = Field(..., description="URL that was visited")
    visit_duration: Optional[int] = Field(None, description="Time spent on page in seconds")
    interaction_type: str = Field("view", description="Type of interaction: view, click, search")


class FrequencyAnalyticsResponse(BaseModel):
    """Model for frequency analytics response."""
    total_visits: int
    unique_pages: int
    avg_visits_per_page: float
    most_visited_pages: List[dict]
    recent_activity: List[dict]
    access_patterns: dict


class QueryCacheStatsResponse(BaseModel):
    """Model for query embedding cache statistics."""
    capacity: int
    size: int
    hits: int
    misses: int
    hit_rate: float
    total_requests: int
    operations_count: int
    expired_evicted: int
    cache_file: str
    ttl_days: float
    auto_save_interval: int


class CachedQueryResponse(BaseModel):
    """Model for cached query information."""
    query: str
    access_count: int
    last_accessed: str
    created_at: str