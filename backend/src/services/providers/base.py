"""Base classes for LLM and embedding providers."""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import httpx
from src.core.logging import get_logger


class BaseProvider(ABC):
    """Base class for all AI providers."""
    
    def __init__(self, api_key: str, timeout: float = 30.0, max_retries: int = 3, retry_delay: float = 1.0):
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get common headers for API requests. Override in subclasses if needed."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    async def _make_request(self, url: str, payload: Dict[str, Any], retries: int = 0) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload
                )
                
                if response.status_code == 200:
                    return response.json()
                
                # Handle rate limiting
                elif response.status_code == 429:
                    if retries < self.max_retries:
                        wait_time = self.retry_delay * (2 ** retries)  # Exponential backoff
                        self.logger.warning(
                            "Rate limited, waiting before retry",
                            extra={
                                "wait_time_seconds": wait_time,
                                "retry_attempt": retries + 1,
                                "max_retries": self.max_retries,
                                "event": "rate_limit_retry"
                            }
                        )
                        await asyncio.sleep(wait_time)
                        return await self._make_request(url, payload, retries + 1)
                    else:
                        raise Exception(f"Rate limit exceeded after {self.max_retries} retries")
                
                # Handle other HTTP errors
                else:
                    error_msg = f"API request failed with status {response.status_code}: {response.text}"
                    if retries < self.max_retries:
                        self.logger.warning(
                            "API request failed, retrying",
                            extra={
                                "status_code": response.status_code,
                                "retry_attempt": retries + 1,
                                "max_retries": self.max_retries,
                                "error_message": error_msg,
                                "event": "api_request_retry"
                            }
                        )
                        await asyncio.sleep(self.retry_delay)
                        return await self._make_request(url, payload, retries + 1)
                    else:
                        raise Exception(error_msg)
        
        except httpx.TimeoutException:
            if retries < self.max_retries:
                self.logger.warning(
                    "Request timeout, retrying",
                    extra={
                        "retry_attempt": retries + 1,
                        "max_retries": self.max_retries,
                        "event": "timeout_retry"
                    }
                )
                await asyncio.sleep(self.retry_delay)
                return await self._make_request(url, payload, retries + 1)
            else:
                raise Exception(f"Request timeout after {self.max_retries} retries")
        
        except Exception as e:
            if retries < self.max_retries:
                self.logger.warning(
                    "Request error, retrying",
                    extra={
                        "retry_attempt": retries + 1,
                        "max_retries": self.max_retries,
                        "error": str(e),
                        "event": "generic_error_retry"
                    }
                )
                await asyncio.sleep(self.retry_delay)
                return await self._make_request(url, payload, retries + 1)
            else:
                raise


class BaseLLMProvider(BaseProvider):
    """Base class for LLM providers."""
    
    @abstractmethod
    async def generate_keywords_and_description(self, title: str, content: str) -> Dict[str, str]:
        """
        Generate keywords, description, and improved title for a web page.
        
        Args:
            title: Page title
            content: Page content
        
        Returns:
            Dict with 'keywords', 'description', and 'improved_title' fields
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check if the LLM API is accessible."""
        pass


class BaseEmbeddingProvider(BaseProvider):
    """Base class for embedding providers."""
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text.
        
        Args:
            text: Text to embed
        
        Returns:
            List of float values representing the embedding vector
        """
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this provider."""
        pass


class CombinedProvider(BaseLLMProvider, BaseEmbeddingProvider):
    """Base class for providers that offer both LLM and embedding services."""
    pass


def _generate_mock_embedding(dimension: int = 2048) -> List[float]:
    """Generate a mock embedding vector for testing/fallback purposes."""
    import random
    import numpy as np
    
    # Generate a random vector with specified dimensions
    random.seed(hash(str(time.time())) % 2**32)
    vector = [random.gauss(0, 1) for _ in range(dimension)]
    
    # Normalize the vector
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = [v / norm for v in vector]
    
    return vector