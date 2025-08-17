"""Factory for creating LLM and embedding providers."""

from typing import Tuple, Optional, TYPE_CHECKING
from src.core.logging import get_logger
from src.services.providers.openai_provider import OpenAIProvider
from src.services.providers.claude_provider import ClaudeProvider
from src.services.providers.groq_provider import GroqProvider
from src.services.providers.ark_provider import ArkProvider
from src.services.providers.base import BaseLLMProvider, BaseEmbeddingProvider

if TYPE_CHECKING:
    from src.core.config import Settings

logger = get_logger(__name__)


class ProviderFactory:
    """Factory for creating LLM and embedding providers based on configuration."""
    
    @staticmethod
    def create_providers(config: "Settings") -> Tuple[Optional[BaseLLMProvider], Optional[BaseEmbeddingProvider]]:
        """
        Create LLM and embedding providers based on configuration.
        
        Args:
            config: Application configuration
            
        Returns:
            Tuple of (llm_provider, embedding_provider)
        """
        try:
            llm_provider = ProviderFactory._create_llm_provider(config)
            embedding_provider = ProviderFactory._create_embedding_provider(config)
            
            logger.info(
                "Providers created successfully",
                extra={
                    "llm_provider": config.llm_provider,
                    "embedding_provider": config.embedding_provider,
                    "event": "providers_created"
                }
            )
            
            return llm_provider, embedding_provider
            
        except Exception as e:
            logger.error(
                "Failed to create providers",
                extra={
                    "error": str(e),
                    "llm_provider": config.llm_provider,
                    "embedding_provider": config.embedding_provider,
                    "event": "provider_creation_failed"
                },
                exc_info=True
            )
            return None, None
    
    @staticmethod
    def _create_llm_provider(config: "Settings") -> Optional[BaseLLMProvider]:
        """Create LLM provider based on configuration."""
        provider_name = config.llm_provider.lower()
        defaults = config.get_provider_defaults().get(provider_name, {})
        
        # Common provider arguments
        provider_kwargs = {
            "api_key": config.get_llm_api_token(),
            "timeout": config.request_timeout,
            "max_retries": config.max_retries,
            "retry_delay": config.retry_delay
        }
        
        try:
            if provider_name == "openai":
                return OpenAIProvider(
                    base_url=config.llm_endpoint or defaults.get("llm_endpoint", "https://api.openai.com/v1"),
                    llm_model=config.llm_model or defaults.get("llm_model", "gpt-4-turbo-preview"),
                    embedding_model=config.embedding_model or defaults.get("embedding_model", "text-embedding-3-large"),
                    **provider_kwargs
                )
            
            elif provider_name == "claude":
                return ClaudeProvider(
                    base_url=config.llm_endpoint or defaults.get("llm_endpoint", "https://api.anthropic.com/v1"),
                    llm_model=config.llm_model or defaults.get("llm_model", "claude-3-sonnet-20240229"),
                    **provider_kwargs
                )
            
            elif provider_name == "groq":
                return GroqProvider(
                    base_url=config.llm_endpoint or defaults.get("llm_endpoint", "https://api.groq.com/openai/v1"),
                    llm_model=config.llm_model or defaults.get("llm_model", "llama3-70b-8192"),
                    **provider_kwargs
                )
            
            elif provider_name == "ark":
                return ArkProvider(
                    llm_endpoint=config.llm_endpoint or defaults.get("llm_endpoint"),
                    embedding_endpoint=config.embedding_endpoint or defaults.get("embedding_endpoint"),
                    llm_model=config.llm_model or defaults.get("llm_model"),
                    embedding_model=config.embedding_model or defaults.get("embedding_model"),
                    **provider_kwargs
                )
            
            else:
                logger.error(f"Unknown LLM provider: {provider_name}")
                return None
                
        except Exception as e:
            logger.error(
                f"Failed to create LLM provider: {provider_name}",
                extra={"error": str(e), "provider": provider_name},
                exc_info=True
            )
            return None
    
    @staticmethod
    def _create_embedding_provider(config: "Settings") -> Optional[BaseEmbeddingProvider]:
        """Create embedding provider based on configuration."""
        provider_name = config.embedding_provider.lower()
        defaults = config.get_provider_defaults().get(provider_name, {})
        
        # Common provider arguments
        provider_kwargs = {
            "api_key": config.get_embedding_api_token(),
            "timeout": config.request_timeout,
            "max_retries": config.max_retries,
            "retry_delay": config.retry_delay
        }
        
        try:
            if provider_name == "openai":
                return OpenAIProvider(
                    base_url=config.embedding_endpoint or defaults.get("embedding_endpoint", "https://api.openai.com/v1"),
                    llm_model=config.llm_model or defaults.get("llm_model", "gpt-4-turbo-preview"),
                    embedding_model=config.embedding_model or defaults.get("embedding_model", "text-embedding-3-large"),
                    **provider_kwargs
                )
            
            elif provider_name == "ark":
                return ArkProvider(
                    llm_endpoint=config.llm_endpoint or defaults.get("llm_endpoint"),
                    embedding_endpoint=config.embedding_endpoint or defaults.get("embedding_endpoint"),
                    llm_model=config.llm_model or defaults.get("llm_model"),
                    embedding_model=config.embedding_model or defaults.get("embedding_model"),
                    **provider_kwargs
                )
            
            # Note: Claude and Groq don't provide embeddings
            elif provider_name in ["claude", "groq"]:
                logger.warning(
                    f"Provider '{provider_name}' does not support embeddings. "
                    "Consider using 'openai' or 'ark' for embeddings."
                )
                return None
            
            else:
                logger.error(f"Unknown embedding provider: {provider_name}")
                return None
                
        except Exception as e:
            logger.error(
                f"Failed to create embedding provider: {provider_name}",
                extra={"error": str(e), "provider": provider_name},
                exc_info=True
            )
            return None
    
    @staticmethod
    def validate_provider_compatibility(config: "Settings") -> Tuple[bool, Optional[str]]:
        """
        Validate that the provider configuration is compatible.
        
        Args:
            config: Application configuration
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if embedding provider supports embeddings
        if config.embedding_provider.lower() in ["claude", "groq"]:
            return False, f"Provider '{config.embedding_provider}' does not support embeddings. Use 'openai' or 'ark' instead."
        
        # Check if LLM and embedding providers can work together
        llm_provider = config.llm_provider.lower()
        embedding_provider = config.embedding_provider.lower()
        
        # If using different providers, ensure they both have API tokens
        if llm_provider != embedding_provider:
            # This is fine - we use the same API token but different endpoints
            pass
        
        # Validate required configuration for ARK
        if llm_provider == "ark" or embedding_provider == "ark":
            defaults = config.get_provider_defaults().get("ark", {})
            if llm_provider == "ark" and not (config.llm_endpoint or defaults.get("llm_endpoint")):
                return False, "ARK LLM provider requires llm_endpoint configuration"
            if embedding_provider == "ark" and not (config.embedding_endpoint or defaults.get("embedding_endpoint")):
                return False, "ARK embedding provider requires embedding_endpoint configuration"
        
        return True, None