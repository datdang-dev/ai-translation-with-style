"""Translation provider interface"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncIterator
from ..models import TranslationRequest, TranslationResult, ProviderConfig


class TranslationProvider(ABC):
    """
    Abstract base class for all translation providers.
    
    This interface defines the contract that all translation providers must implement,
    ensuring consistent behavior across different AI services (OpenRouter, OpenAI, etc.).
    """
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize the provider with configuration.
        
        Args:
            config: Provider-specific configuration including auth, models, etc.
        """
        self.config = config
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the unique name of this provider.
        
        Returns:
            Provider name (should match config.name)
        """
        pass
    
    @property
    @abstractmethod
    def provider_type(self) -> str:
        """
        Get the type of this provider.
        
        Returns:
            Provider type (e.g., "openrouter", "openai", "anthropic")
        """
        pass
    
    @abstractmethod
    async def translate(self, request: TranslationRequest) -> TranslationResult:
        """
        Translate text according to the request parameters.
        
        This is the core method that performs the actual translation.
        Implementations should:
        1. Validate the request
        2. Select appropriate model/settings
        3. Make API call(s) to the provider
        4. Handle errors and retries
        5. Return a properly formatted result
        
        Args:
            request: Translation request with text and parameters
            
        Returns:
            Translation result with translated text or error information
            
        Raises:
            ProviderError: For provider-specific errors
            ValidationError: For invalid request parameters
        """
        pass
    
    @abstractmethod
    async def translate_streaming(
        self, 
        request: TranslationRequest
    ) -> AsyncIterator[str]:
        """
        Translate text with streaming response (if supported).
        
        Yields partial translation results as they become available.
        If streaming is not supported, should raise NotImplementedError.
        
        Args:
            request: Translation request with text and parameters
            
        Yields:
            Partial translation strings
            
        Raises:
            NotImplementedError: If streaming is not supported
            ProviderError: For provider-specific errors
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and can accept requests.
        
        This should be a lightweight check that verifies:
        1. API keys are valid
        2. Service is reachable
        3. Rate limits allow requests
        
        Returns:
            True if provider is healthy, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_available_models(self) -> list[str]:
        """
        Get list of models available from this provider.
        
        Returns:
            List of model identifiers that can be used in requests
        """
        pass
    
    @abstractmethod
    async def estimate_cost(
        self, 
        request: TranslationRequest
    ) -> Optional[float]:
        """
        Estimate the cost of a translation request.
        
        Args:
            request: Translation request to estimate cost for
            
        Returns:
            Estimated cost in USD, or None if cost estimation is not available
        """
        pass
    
    async def validate_request(self, request: TranslationRequest) -> None:
        """
        Validate that a request can be handled by this provider.
        
        Default implementation checks basic compatibility.
        Providers can override for additional validation.
        
        Args:
            request: Request to validate
            
        Raises:
            ValidationError: If request is invalid for this provider
        """
        # Check if requested model is available
        if request.model_name:
            available_models = await self.get_available_models()
            if request.model_name not in available_models:
                raise ValueError(
                    f"Model '{request.model_name}' not available. "
                    f"Available models: {', '.join(available_models)}"
                )
        
        # Check text length limits
        model_config = self.config.get_model(request.model_name)
        if model_config and model_config.max_input_tokens:
            # Rough token estimation (4 chars per token)
            estimated_tokens = len(request.text) // 4
            if estimated_tokens > model_config.max_input_tokens:
                raise ValueError(
                    f"Text too long: ~{estimated_tokens} tokens, "
                    f"max allowed: {model_config.max_input_tokens}"
                )
    
    async def close(self) -> None:
        """
        Clean up provider resources.
        
        Default implementation does nothing.
        Providers should override if they need cleanup.
        """
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name='{self.name}', "
            f"type='{self.provider_type}', "
            f"enabled={self.config.enabled})"
        )