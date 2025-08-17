"""Groq provider for LLM services."""

import json
from typing import List, Dict, Any
from datetime import datetime
from .base import BaseLLMProvider, _generate_mock_embedding


class GroqProvider(BaseLLMProvider):
    """Groq provider for LLM services. Note: Groq uses OpenAI-compatible endpoints."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.groq.com/openai/v1", 
                 llm_model: str = "llama3-70b-8192", **kwargs):
        super().__init__(api_key, **kwargs)
        self.base_url = base_url.rstrip('/')
        self.llm_model = llm_model
        self.llm_endpoint = f"{self.base_url}/chat/completions"
    
    async def generate_keywords_and_description(self, title: str, content: str) -> Dict[str, str]:
        """Generate keywords, description, and improved title using Groq's LLM."""
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
            
            # Extract content from response (OpenAI-compatible format)
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
                "Error generating keywords/description with Groq",
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
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if the Groq API is accessible."""
        try:
            # Simple test request to Groq API
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


class GroqEmbeddingProvider:
    """
    Placeholder class for Groq embeddings.
    
    Note: Groq focuses on LLM inference and doesn't currently provide embedding services.
    This class exists for consistency but will raise NotImplementedError.
    Use OpenAI or another provider for embeddings when using Groq for LLM.
    """
    
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "Groq does not provide embedding services. "
            "Use OpenAI or another provider for embeddings."
        )
    
    async def generate_embedding(self, text: str) -> List[float]:
        raise NotImplementedError(
            "Groq does not provide embedding services. "
            "Use OpenAI or another provider for embeddings."
        )
    
    def get_embedding_dimension(self) -> int:
        raise NotImplementedError(
            "Groq does not provide embedding services. "
            "Use OpenAI or another provider for embeddings."
        )