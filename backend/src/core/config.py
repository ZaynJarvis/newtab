"""Configuration settings for the New Tab backend service."""

import os
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings using pydantic-settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API Configuration
    ark_api_token: str = Field(
        ...,
        description="ByteDance ARK API token for LLM and embeddings"
    )
    
    # Server Configuration
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind the server to"
    )
    port: int = Field(
        default=8000,
        description="Port to bind the server to"
    )
    reload: bool = Field(
        default=True,
        description="Enable auto-reload for development"
    )
    log_level: str = Field(
        default="info",
        description="Logging level"
    )
    
    # API Endpoints
    llm_endpoint: str = Field(
        default="https://ark-cn-beijing.bytedance.net/api/v3/chat/completions",
        description="ByteDance ARK LLM endpoint"
    )
    embedding_endpoint: str = Field(
        default="https://ark-cn-beijing.bytedance.net/api/v3/embeddings/multimodal",
        description="ByteDance ARK embedding endpoint"
    )
    
    # Model Configuration
    llm_model: str = Field(
        default="ep-20250529215531-dfpgt",
        description="LLM model identifier"
    )
    embedding_model: str = Field(
        default="ep-20250529220411-grkkv",
        description="Embedding model identifier"
    )
    
    # Vector Store Configuration
    vector_dimension: int = Field(
        default=2048,
        description="Dimension of the embedding vectors"
    )
    max_vectors: int = Field(
        default=10000,
        description="Maximum number of vectors to store in memory"
    )
    
    # API Client Configuration
    max_retries: int = Field(
        default=3,
        description="Maximum number of API request retries"
    )
    retry_delay: float = Field(
        default=1.0,
        description="Base delay between retries in seconds"
    )
    request_timeout: float = Field(
        default=30.0,
        description="Request timeout in seconds"
    )
    health_check_timeout: float = Field(
        default=5.0,
        description="Health check timeout in seconds"
    )
    
    # Cache Configuration
    query_cache_capacity: int = Field(
        default=1000,
        description="Query embedding cache capacity"
    )
    query_cache_ttl_days: int = Field(
        default=7,
        description="Query cache TTL in days"
    )
    query_cache_file: str = Field(
        default="query_embeddings_cache.json",
        description="Query cache file name"
    )
    
    # Database Configuration
    database_file: str = Field(
        default="web_memory.db",
        description="SQLite database file name"
    )
    
    @field_validator("ark_api_token")
    @classmethod
    def validate_api_token(cls, v: str) -> str:
        """Validate that the API token is not empty."""
        if not v or v.strip() == "":
            raise ValueError("ARK_API_TOKEN cannot be empty")
        return v.strip()
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"debug", "info", "warning", "error", "critical"}
        if v.lower() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.lower()


def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()


# Export commonly used settings
settings = get_settings()