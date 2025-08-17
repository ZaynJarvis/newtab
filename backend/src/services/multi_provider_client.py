"""Multi-provider API client for LLM and embeddings generation."""

import os
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from src.cache.query_embedding_cache import QueryEmbeddingCache
from src.core.logging import get_logger
from src.services.provider_factory import ProviderFactory
from src.services.providers.base import BaseLLMProvider, BaseEmbeddingProvider

if TYPE_CHECKING:
    from src.core.config import Settings


class MultiProviderAPIClient:
    """Multi-provider client for LLM and embedding services."""
    
    def __init__(self, config: Optional["Settings"] = None, api_key: Optional[str] = None):
        self.logger = get_logger(__name__)
        self.config = config
        
        if config:
            # Use new configuration system
            self.llm_provider, self.embedding_provider = ProviderFactory.create_providers(config)
            
            # Initialize query embedding cache with config
            self.query_cache = QueryEmbeddingCache(
                capacity=config.query_cache_capacity,
                cache_file=config.query_cache_file,
                ttl_days=config.query_cache_ttl_days
            )
        else:
            # Fallback to old system for backward compatibility
            # This maintains compatibility with existing code that doesn't use config
            from src.services.api_client import ArkAPIClient
            self._legacy_client = ArkAPIClient(api_key=api_key)
            self.llm_provider = None
            self.embedding_provider = None
            self.query_cache = self._legacy_client.query_cache if hasattr(self._legacy_client, 'query_cache') else None
    
    async def generate_keywords_and_description(self, title: str, content: str) -> Dict[str, str]:
        """
        Generate keywords, description, and improved title for a web page using LLM.
        
        Args:
            title: Page title
            content: Page content (truncated for API limits)
        
        Returns:
            Dict with 'keywords', 'description', and 'improved_title' fields
        """
        # Use legacy client for backward compatibility
        if hasattr(self, '_legacy_client'):
            return await self._legacy_client.generate_keywords_and_description(title, content)
        
        # Use new provider system
        if not self.llm_provider:
            self.logger.warning("No LLM provider available, returning fallback response")
            return {
                "keywords": "web page, content",
                "description": f"Content from {title}",
                "improved_title": title
            }
        
        try:
            return await self.llm_provider.generate_keywords_and_description(title, content)
        except Exception as e:
            self.logger.error(
                "Error with LLM provider, returning fallback response",
                extra={
                    "error": str(e),
                    "provider": type(self.llm_provider).__name__,
                    "event": "llm_provider_error"
                },
                exc_info=True
            )
            return {
                "keywords": "web page, content",
                "description": f"Content from {title}",
                "improved_title": title
            }
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text using embedding provider with LRU caching.
        
        Implements 3-step fallback strategy:
        1. Check cache for exact match
        2. Call API and cache result if successful
        3. Return mock embedding if API fails
        
        Args:
            text: Text to embed (will be truncated if too long)
        
        Returns:
            List of float values representing the embedding vector
        """
        # Use legacy client for backward compatibility
        if hasattr(self, '_legacy_client'):
            return await self._legacy_client.generate_embedding(text)
        
        # Truncate text to avoid API limits
        max_text_length = 3000
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."
        
        # Step 1: Check cache for exact match
        if self.query_cache:
            cached_embedding = self.query_cache.get(text)
            if cached_embedding is not None:
                self.logger.debug(
                    "Using cached embedding for query",
                    extra={
                        "query_preview": text[:50],
                        "event": "embedding_cache_hit"
                    }
                )
                return cached_embedding
        
        # Step 2: Call embedding API and cache result
        if not self.embedding_provider:
            self.logger.warning("No embedding provider available, using mock embedding")
            return self._generate_mock_embedding()
        
        try:
            embedding = await self.embedding_provider.generate_embedding(text)
            
            # Cache successful API response
            if self.query_cache and embedding:
                self.query_cache.put(text, embedding)
                self.logger.info(
                    "Generated and cached new embedding for query",
                    extra={
                        "query_preview": text[:50],
                        "embedding_dimension": len(embedding),
                        "provider": type(self.embedding_provider).__name__,
                        "event": "embedding_generated"
                    }
                )
            
            return embedding
        
        except Exception as e:
            self.logger.error(
                "Error with embedding provider, using mock",
                extra={
                    "error": str(e),
                    "provider": type(self.embedding_provider).__name__,
                    "query_preview": text[:50],
                    "event": "embedding_provider_error"
                },
                exc_info=True
            )
            return self._generate_mock_embedding()
    
    def _generate_mock_embedding(self) -> List[float]:
        """Generate a mock embedding vector for testing."""
        import random
        import numpy as np
        import time
        
        # Determine dimension based on provider or use default
        dimension = 2048  # Default
        if self.embedding_provider and hasattr(self.embedding_provider, 'get_embedding_dimension'):
            try:
                dimension = self.embedding_provider.get_embedding_dimension()
            except:
                pass
        elif self.config:
            # Try to get dimension from config defaults
            defaults = self.config.get_provider_defaults().get(self.config.embedding_provider, {})
            dimension = defaults.get('embedding_dimension', 2048)
        
        # Generate a random vector
        random.seed(hash(str(time.time())) % 2**32)
        vector = [random.gauss(0, 1) for _ in range(dimension)]
        
        # Normalize the vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if the API providers are accessible with timeout protection."""
        # Use legacy client for backward compatibility
        if hasattr(self, '_legacy_client'):
            return await self._legacy_client.health_check()
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "llm_provider": None,
            "embedding_provider": None
        }
        
        # Check LLM provider
        if self.llm_provider:
            try:
                llm_health = await self.llm_provider.health_check()
                health_status["llm_provider"] = {
                    "provider_type": type(self.llm_provider).__name__,
                    "status": llm_health.get("status", "unknown"),
                    "response_time_ms": llm_health.get("response_time_ms"),
                    "model": llm_health.get("model")
                }
                if llm_health.get("status") != "healthy":
                    health_status["status"] = "degraded"
            except Exception as e:
                health_status["llm_provider"] = {
                    "provider_type": type(self.llm_provider).__name__,
                    "status": "error",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
        else:
            health_status["llm_provider"] = {"status": "unavailable"}
            health_status["status"] = "degraded"
        
        # Check embedding provider
        if self.embedding_provider:
            try:
                # Embedding providers don't typically have health checks,
                # so we'll just check if they're initialized
                health_status["embedding_provider"] = {
                    "provider_type": type(self.embedding_provider).__name__,
                    "status": "available",
                    "dimension": getattr(self.embedding_provider, 'get_embedding_dimension', lambda: None)()
                }
            except Exception as e:
                health_status["embedding_provider"] = {
                    "provider_type": type(self.embedding_provider).__name__,
                    "status": "error",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
        else:
            health_status["embedding_provider"] = {"status": "unavailable"}
            health_status["status"] = "degraded"
        
        return health_status
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get query embedding cache statistics."""
        if hasattr(self, '_legacy_client'):
            return self._legacy_client.get_cache_stats()
        
        if self.query_cache:
            return self.query_cache.get_stats()
        return {"error": "No cache available"}
    
    def clear_cache(self) -> bool:
        """Clear query embedding cache."""
        if hasattr(self, '_legacy_client'):
            return self._legacy_client.clear_cache()
        
        if self.query_cache:
            self.query_cache.clear()
            return True
        return False
    
    def cleanup_cache(self) -> int:
        """Clean up expired cache entries. Returns number of removed entries."""
        if hasattr(self, '_legacy_client'):
            return self._legacy_client.cleanup_cache()
        
        if self.query_cache:
            return self.query_cache.cleanup_expired()
        return 0
    
    def get_top_cached_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequently cached queries for debugging."""
        if hasattr(self, '_legacy_client'):
            return self._legacy_client.get_top_cached_queries(limit)
        
        if self.query_cache:
            return self.query_cache.get_top_queries(limit)
        return []