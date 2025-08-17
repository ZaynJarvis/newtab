"""OpenAI provider for LLM and embedding services."""

import json
from typing import List, Dict, Any
from datetime import datetime
from .base import CombinedProvider, _generate_mock_embedding


class OpenAIProvider(CombinedProvider):
    """OpenAI provider for both LLM and embedding services."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", 
                 llm_model: str = "gpt-4-turbo-preview", embedding_model: str = "text-embedding-3-large",
                 **kwargs):
        super().__init__(api_key, **kwargs)
        self.base_url = base_url.rstrip('/')
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.llm_endpoint = f"{self.base_url}/chat/completions"
        self.embedding_endpoint = f"{self.base_url}/embeddings"
    
    async def generate_keywords_and_description(self, title: str, content: str) -> Dict[str, str]:
        """Generate keywords, description, and improved title using OpenAI's chat completion."""
        # Truncate content to avoid token limits
        max_content_length = 2000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        prompt = f"""Analyze this web page and generate:
1. Keywords: 5-10 relevant keywords/phrases separated by commas
2. Description: A concise 1-2 sentence summary
3. Title evaluation: Check if the title is generic (like "Docs", "Document", "Home", "Index", etc.) and suggest a better, more descriptive title based on the content if needed

Title: {title}
Content: {content}

Evaluate the title quality:
- If the title is generic, vague, or not descriptive (like "Docs", "Document", "Home", "Index", "Page", etc.), suggest a better title based on the actual content
- If the title is already descriptive and specific, keep it as is
- The improved title should be concise but informative, reflecting the main topic or purpose of the page

Please respond in this exact JSON format:
{{
    "keywords": "keyword1, keyword2, keyword3, ...",
    "description": "Brief description of the page content",
    "improved_title": "Better title if original is generic, or original title if already good"
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
            "max_tokens": 400
        }
        
        try:
            response = await self._make_request(self.llm_endpoint, payload)
            
            # Extract content from response
            if "choices" in response and len(response["choices"]) > 0:
                response_content = response["choices"][0]["message"]["content"]
                
                # Try to parse JSON response
                try:
                    # Clean up response (remove code block markers if present)
                    response_content = response_content.strip()
                    if response_content.startswith("```json"):
                        response_content = response_content[7:]
                    if response_content.endswith("```"):
                        response_content = response_content[:-3]
                    response_content = response_content.strip()
                    
                    result = json.loads(response_content)
                    
                    return {
                        "keywords": result.get("keywords", ""),
                        "description": result.get("description", ""),
                        "improved_title": result.get("improved_title", title)
                    }
                
                except json.JSONDecodeError:
                    # Fallback: extract manually
                    lines = response_content.split('\n')
                    keywords = ""
                    description = ""
                    improved_title = title
                    
                    for line in lines:
                        line = line.strip()
                        if "keywords" in line.lower() and ":" in line:
                            keywords = line.split(":", 1)[1].strip().strip('"')
                        elif "description" in line.lower() and ":" in line:
                            description = line.split(":", 1)[1].strip().strip('"')
                        elif "improved_title" in line.lower() and ":" in line:
                            improved_title = line.split(":", 1)[1].strip().strip('"')
                    
                    return {
                        "keywords": keywords,
                        "description": description,
                        "improved_title": improved_title or title
                    }
            
            # Fallback response
            return {
                "keywords": "web page, content",
                "description": "Web page content",
                "improved_title": title
            }
        
        except Exception as e:
            self.logger.error(
                "Error generating keywords/description",
                extra={
                    "error": str(e),
                    "title": title[:100],
                    "content_length": len(content),
                    "event": "keywords_generation_error"
                },
                exc_info=True
            )
            return {
                "keywords": "web page, content",
                "description": f"Content from {title}",
                "improved_title": title
            }
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate vector embedding using OpenAI's embeddings API."""
        # Truncate text to avoid API limits
        max_text_length = 8000  # OpenAI's text-embedding-3-large can handle up to 8191 tokens
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."
        
        payload = {
            "model": self.embedding_model,
            "input": text,
            "encoding_format": "float"
        }
        
        try:
            response = await self._make_request(self.embedding_endpoint, payload)
            
            # Extract embedding from response
            if "data" in response and len(response["data"]) > 0:
                embedding = response["data"][0].get("embedding", [])
                if embedding:
                    self.logger.debug(
                        "Generated new embedding",
                        extra={
                            "text_preview": text[:50],
                            "embedding_dimension": len(embedding),
                            "event": "embedding_generated"
                        }
                    )
                    return embedding
            
            # Fallback: return mock embedding
            self.logger.warning(
                "Could not extract embedding from OpenAI response, using mock",
                extra={
                    "response_structure": str(response)[:500],
                    "event": "embedding_fallback_mock"
                }
            )
            return _generate_mock_embedding(self.get_embedding_dimension())
        
        except Exception as e:
            self.logger.error(
                "Error generating OpenAI embedding, using mock",
                extra={
                    "error": str(e),
                    "text_preview": text[:50],
                    "event": "embedding_error_fallback"
                },
                exc_info=True
            )
            return _generate_mock_embedding(self.get_embedding_dimension())
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of OpenAI embeddings."""
        # text-embedding-3-large produces 3072-dimensional embeddings
        # text-embedding-3-small produces 1536-dimensional embeddings
        # text-embedding-ada-002 produces 1536-dimensional embeddings
        if "3-large" in self.embedding_model:
            return 3072
        elif "3-small" in self.embedding_model:
            return 1536
        elif "ada-002" in self.embedding_model:
            return 1536
        else:
            # Default to 3072 for newer models
            return 3072
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if the OpenAI API is accessible."""
        try:
            # Simple test request to chat completion API
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
            
            start_time = datetime.now()
            response = await self._make_request(self.llm_endpoint, payload)
            response_time = (datetime.now() - start_time).total_seconds()
            
            if "choices" in response and len(response["choices"]) > 0:
                return {
                    "status": "healthy",
                    "llm_api": "accessible",
                    "response_time_ms": round(response_time * 1000, 2),
                    "model": self.llm_model,
                    "embedding_model": self.embedding_model,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "llm_api": "error",
                    "error": "Unexpected response format",
                    "timestamp": datetime.now().isoformat()
                }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "llm_api": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }