"""Data models for the Local Web Memory backend service."""

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