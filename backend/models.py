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


class KeywordSearchResponse(BaseModel):
    """Model for keyword search results."""
    results: List[PageResponse]
    total_found: int
    query: str


class VectorSearchResponse(BaseModel):
    """Model for vector search results."""
    results: List[dict]  # PageResponse + similarity_score
    total_found: int
    query: str


class HealthResponse(BaseModel):
    """Model for health check response."""
    status: str
    timestamp: datetime
    database_connected: bool
    total_pages: int


class CombinedSearchResponse(BaseModel):
    """Model for combined search results."""
    results: List[dict]  # PageResponse + combined_score + keyword_score + semantic_score
    total_found: int
    query: str
    keyword_results_count: int
    semantic_results_count: int


class IndexResponse(BaseModel):
    """Model for indexing response."""
    id: int
    status: str
    message: str
    processing_time: float