"""Configuration settings for the New Tab backend service."""

import os
from typing import Optional, Dict, Any
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings using pydantic-settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # LLM API Configuration
    llm_api_token: str = Field(
        description="API token for LLM provider"
    )
    
    # Embedding API Configuration  
    embedding_api_token: str = Field(
        description="API token for embedding provider"
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
    
    # Provider Configuration
    llm_provider: str = Field(
        default="openai",
        description="LLM provider (openai, claude, groq, ark)"
    )
    embedding_provider: str = Field(
        default="openai",
        description="Embedding provider (openai, ark)"
    )
    
    # API Endpoints (provider-specific)
    llm_endpoint: Optional[str] = Field(
        default=None,
        description="Custom LLM endpoint URL (overrides provider defaults)"
    )
    embedding_endpoint: Optional[str] = Field(
        default=None,
        description="Custom embedding endpoint URL (overrides provider defaults)"
    )
    
    # Model Configuration
    llm_model: Optional[str] = Field(
        default=None,
        description="LLM model identifier (uses provider defaults if not specified)"
    )
    embedding_model: Optional[str] = Field(
        default=None,
        description="Embedding model identifier (uses provider defaults if not specified)"
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
    
    
    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider."""
        valid_providers = {"openai", "claude", "groq", "ark"}
        if v.lower() not in valid_providers:
            raise ValueError(f"llm_provider must be one of {valid_providers}")
        return v.lower()
    
    @field_validator("embedding_provider")
    @classmethod
    def validate_embedding_provider(cls, v: str) -> str:
        """Validate embedding provider."""
        valid_providers = {"openai", "ark"}
        if v.lower() not in valid_providers:
            raise ValueError(f"embedding_provider must be one of {valid_providers}")
        return v.lower()
    
    
    def get_provider_defaults(self) -> Dict[str, Dict[str, Any]]:
        """Get default configurations for each provider."""
        return {
            "openai": {
                "llm_endpoint": "https://api.openai.com/v1/chat/completions",
                "embedding_endpoint": "https://api.openai.com/v1/embeddings",
                "llm_model": "gpt-4-turbo-preview",
                "embedding_model": "text-embedding-3-large",
                "embedding_dimension": 3072
            },
            "claude": {
                "llm_endpoint": "https://api.anthropic.com/v1/messages",
                "llm_model": "claude-3-sonnet-20240229"
            },
            "groq": {
                "llm_endpoint": "https://api.groq.com/openai/v1/chat/completions",
                "llm_model": "llama3-70b-8192"
            },
            "ark": {
                "llm_endpoint": "https://ark-cn-beijing.bytedance.net/api/v3/chat/completions",
                "embedding_endpoint": "https://ark-cn-beijing.bytedance.net/api/v3/embeddings/multimodal",
                "llm_model": "ep-20250529215531-dfpgt",
                "embedding_model": "ep-20250529220411-grkkv",
                "embedding_dimension": 2048
            }
        }
    
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