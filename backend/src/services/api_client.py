"""ByteDance Ark API client for LLM and embeddings generation."""

import os
import asyncio
import json
from typing import List, Optional, Dict, Any, TYPE_CHECKING
import httpx
import time
from datetime import datetime
from src.cache.query_embedding_cache import QueryEmbeddingCache

if TYPE_CHECKING:
    from src.core.config import Settings


class ArkAPIClient:
    """Client for ByteDance Ark API services."""
    
    def __init__(self, config: Optional["Settings"] = None, api_key: Optional[str] = None):
        """Initialize the API client."""
        if config:
            # Use new configuration system
            self.api_key = config.ark_api_token
            self.llm_endpoint = config.llm_endpoint
            self.embedding_endpoint = config.embedding_endpoint
            self.llm_model = config.llm_model
            self.embedding_model = config.embedding_model
            self.max_retries = config.max_retries
            self.retry_delay = config.retry_delay
            self.request_timeout = config.request_timeout
            self.health_check_timeout = config.health_check_timeout
            
            # Initialize query embedding cache with config
            self.query_cache = QueryEmbeddingCache(
                capacity=config.query_cache_capacity,
                cache_file=config.query_cache_file,
                ttl_days=config.query_cache_ttl_days
            )
        else:
            # Fallback to old system for backward compatibility
            self.api_key = api_key or os.getenv("ARK_API_TOKEN")
            if not self.api_key:
                raise ValueError("ARK_API_TOKEN environment variable is required")
            
            self.llm_endpoint = "https://ark-cn-beijing.bytedance.net/api/v3/chat/completions"
            self.embedding_endpoint = "https://ark-cn-beijing.bytedance.net/api/v3/embeddings/multimodal"
            self.llm_model = "ep-20250529215531-dfpgt"
            self.embedding_model = "ep-20250529220411-grkkv"
            
            # Rate limiting and retry configuration
            self.max_retries = 3
            self.retry_delay = 1.0  # seconds
            self.request_timeout = 30.0  # seconds
            self.health_check_timeout = 5.0  # shorter timeout for health checks
            
            # Initialize query embedding cache
            self.query_cache = QueryEmbeddingCache(
                capacity=1000,
                cache_file="query_embeddings_cache.json",
                ttl_days=7
            )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get common headers for API requests."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    async def _make_request(self, url: str, payload: Dict[str, Any], retries: int = 0) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        try:
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
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
                        print(f"Rate limited, waiting {wait_time}s before retry {retries + 1}/{self.max_retries}")
                        await asyncio.sleep(wait_time)
                        return await self._make_request(url, payload, retries + 1)
                    else:
                        raise Exception(f"Rate limit exceeded after {self.max_retries} retries")
                
                # Handle other HTTP errors
                else:
                    error_msg = f"API request failed with status {response.status_code}: {response.text}"
                    if retries < self.max_retries:
                        print(f"Request failed, retrying {retries + 1}/{self.max_retries}: {error_msg}")
                        await asyncio.sleep(self.retry_delay)
                        return await self._make_request(url, payload, retries + 1)
                    else:
                        raise Exception(error_msg)
        
        except httpx.TimeoutException:
            if retries < self.max_retries:
                print(f"Request timeout, retrying {retries + 1}/{self.max_retries}")
                await asyncio.sleep(self.retry_delay)
                return await self._make_request(url, payload, retries + 1)
            else:
                raise Exception(f"Request timeout after {self.max_retries} retries")
        
        except Exception as e:
            if retries < self.max_retries:
                print(f"Request error, retrying {retries + 1}/{self.max_retries}: {str(e)}")
                await asyncio.sleep(self.retry_delay)
                return await self._make_request(url, payload, retries + 1)
            else:
                raise
    
    async def generate_keywords_and_description(self, title: str, content: str) -> Dict[str, str]:
        """
        Generate keywords and description for a web page using LLM.
        
        Args:
            title: Page title
            content: Page content (truncated for API limits)
        
        Returns:
            Dict with 'keywords' and 'description' fields
        """
        # Truncate content to avoid token limits
        max_content_length = 2000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        prompt = f"""Analyze this web page and generate:
1. Keywords: 5-10 relevant keywords/phrases separated by commas
2. Description: A concise 1-2 sentence summary

Title: {title}
Content: {content}

Please respond in this exact JSON format:
{{
    "keywords": "keyword1, keyword2, keyword3, ...",
    "description": "Brief description of the page content"
}}"""
        
        payload = {
            "model": self.llm_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 300
        }
        
        try:
            response = await self._make_request(self.llm_endpoint, payload)
            
            # Extract content from response
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]
                
                # Try to parse JSON response
                try:
                    # Clean up response (remove code block markers if present)
                    content = content.strip()
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()
                    
                    result = json.loads(content)
                    
                    return {
                        "keywords": result.get("keywords", ""),
                        "description": result.get("description", "")
                    }
                
                except json.JSONDecodeError:
                    # Fallback: extract manually
                    lines = content.split('\n')
                    keywords = ""
                    description = ""
                    
                    for line in lines:
                        line = line.strip()
                        if "keywords" in line.lower() and ":" in line:
                            keywords = line.split(":", 1)[1].strip().strip('"')
                        elif "description" in line.lower() and ":" in line:
                            description = line.split(":", 1)[1].strip().strip('"')
                    
                    return {
                        "keywords": keywords,
                        "description": description
                    }
            
            # Fallback response
            return {
                "keywords": "web page, content",
                "description": "Web page content"
            }
        
        except Exception as e:
            print(f"Error generating keywords/description: {str(e)}")
            return {
                "keywords": "web page, content",
                "description": f"Content from {title}"
            }
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text using ByteDance embedding API with LRU caching.
        
        Implements 3-step fallback strategy:
        1. Check cache for exact match
        2. Call API and cache result if successful
        3. Return mock embedding if API fails
        
        Args:
            text: Text to embed (will be truncated if too long)
        
        Returns:
            List of float values representing the embedding vector
        """
        # Truncate text to avoid API limits
        max_text_length = 3000
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."
        
        # Step 1: Check cache for exact match
        cached_embedding = self.query_cache.get(text)
        if cached_embedding is not None:
            print(f"Using cached embedding for query: {text[:50]}...")
            return cached_embedding
        
        # Step 2: Call embedding API and cache result
        payload = {
            "model": self.embedding_model,
            "input": [
                {
                    "type": "text",
                    "text": text
                }
            ]
        }
        
        try:
            response = await self._make_request(self.embedding_endpoint, payload)
            
            # Extract embedding from response - handle the actual API structure
            embedding = None
            if "data" in response:
                # The API returns data as a dict with "embedding" key, not a list
                if isinstance(response["data"], dict) and "embedding" in response["data"]:
                    embedding = response["data"]["embedding"]
                # Handle if data is a list (old format)
                elif isinstance(response["data"], list) and len(response["data"]) > 0:
                    embedding = response["data"][0].get("embedding", [])
            
            if embedding:
                # Cache successful API response
                self.query_cache.put(text, embedding)
                print(f"Generated and cached new embedding for query: {text[:50]}...")
                return embedding
            
            # Fallback: return mock embedding
            print("Warning: Could not extract embedding from API response, using mock")
            print(f"Response structure: {response}")
            return self._generate_mock_embedding()
        
        except Exception as e:
            print(f"Error generating embedding: {str(e)}, using mock")
            return self._generate_mock_embedding()
    
    def _generate_mock_embedding(self) -> List[float]:
        """Generate a mock embedding vector for testing."""
        import random
        import numpy as np
        
        # Generate a random vector with 2048 dimensions (ByteDance embedding size)
        random.seed(hash(str(time.time())) % 2**32)
        vector = [random.gauss(0, 1) for _ in range(2048)]
        
        # Normalize the vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if the API is accessible with timeout protection."""
        try:
            # Simple test request to LLM API with short timeout
            payload = {
                "model": self.llm_model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello"
                    }
                ],
                "max_tokens": 10
            }
            
            start_time = time.time()
            
            # Use asyncio.wait_for to enforce timeout
            try:
                async with httpx.AsyncClient(timeout=self.health_check_timeout) as client:
                    response = await asyncio.wait_for(
                        client.post(
                            self.llm_endpoint,
                            headers=self._get_headers(),
                            json=payload
                        ),
                        timeout=self.health_check_timeout
                    )
                    
                    response_time = time.time() - start_time
                    
                    if response.status_code == 200:
                        return {
                            "status": "healthy",
                            "llm_api": "accessible",
                            "response_time_ms": round(response_time * 1000, 2),
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "llm_api": "error",
                            "error": f"HTTP {response.status_code}: {response.text}",
                            "timestamp": datetime.now().isoformat()
                        }
            
            except asyncio.TimeoutError:
                return {
                    "status": "unhealthy",
                    "llm_api": "timeout",
                    "error": f"Health check timed out after {self.health_check_timeout}s",
                    "timestamp": datetime.now().isoformat()
                }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "llm_api": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get query embedding cache statistics."""
        return self.query_cache.get_stats()
    
    def clear_cache(self) -> bool:
        """Clear query embedding cache."""
        self.query_cache.clear()
        return True
    
    def cleanup_cache(self) -> int:
        """Clean up expired cache entries. Returns number of removed entries."""
        return self.query_cache.cleanup_expired()
    
    def get_top_cached_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequently cached queries for debugging."""
        return self.query_cache.get_top_queries(limit)