"""OpenRouter translation provider implementation"""

import json
import asyncio
from typing import Optional, Dict, Any, AsyncIterator, List
from datetime import datetime, timezone

from ...core.interfaces import TranslationProvider
from ...core.models import (
    TranslationRequest, TranslationResult, TranslationStatus, 
    TranslationError, ErrorType, TranslationMetrics, ProviderConfig
)
from ..http import AsyncHTTPClient, HTTPError, RetryHandler, create_provider_retry_handler
from ..key_manager import InMemoryKeyManager
from ..observability import get_logger, get_tracer


class OpenRouterProvider(TranslationProvider):
    """
    OpenRouter API translation provider.
    
    Supports multiple AI models through the OpenRouter API with:
    - Automatic API key rotation
    - Rate limiting and retry logic
    - Cost estimation
    - Streaming responses (if supported by model)
    - Comprehensive error handling
    """
    
    def __init__(self, config: ProviderConfig, key_manager: InMemoryKeyManager):
        """
        Initialize OpenRouter provider.
        
        Args:
            config: Provider configuration
            key_manager: API key manager instance
        """
        super().__init__(config)
        self.key_manager = key_manager
        self.http_client = AsyncHTTPClient(
            timeout_seconds=config.timeout_seconds,
            max_connections=20,
            max_connections_per_host=10
        )
        self.retry_handler = create_provider_retry_handler(
            max_retries=config.retry_config.max_retries,
            initial_delay=config.retry_config.initial_delay_seconds,
            max_delay=config.retry_config.max_delay_seconds
        )
        
        self.logger = get_logger("openrouter_provider")
        self.tracer = get_tracer()
        
        # Initialize API keys
        self._initialize_keys()
    
    def _initialize_keys(self) -> None:
        """Initialize API keys in the key manager"""
        for i, api_key in enumerate(self.config.api_keys):
            asyncio.create_task(self.key_manager.add_key(
                provider_name=self.config.name,
                api_key=str(api_key.get_secret_value()),
                metadata={"key_index": i}
            ))
    
    @property
    def name(self) -> str:
        """Get provider name"""
        return self.config.name
    
    @property
    def provider_type(self) -> str:
        """Get provider type"""
        return "openrouter"
    
    async def translate(self, request: TranslationRequest) -> TranslationResult:
        """
        Translate text using OpenRouter API.
        
        Args:
            request: Translation request
            
        Returns:
            Translation result
        """
        # Create result object
        result = TranslationResult(
            request_id=request.request_id,
            status=TranslationStatus.PENDING,
            original_text=request.text,
            target_language=request.target_language
        )
        
        try:
            # Validate request
            await self.validate_request(request)
            
            # Mark as started
            result.mark_started()
            
            # Get model configuration
            model_config = self.config.get_model(request.model_name)
            model_name = request.model_name or self.config.default_model
            
            if not model_name:
                raise ValueError("No model specified and no default model configured")
            
            # Create translation with tracing
            with self.tracer.trace_translation_request(
                request.request_id, self.name, model_name, len(request.text)
            ):
                translated_text = await self._perform_translation(request, model_name)
            
            # Create metrics
            processing_time = result.total_processing_time_ms or 0
            metrics = TranslationMetrics(
                processing_time_ms=processing_time,
                provider_name=self.name,
                model_name=model_name,
                confidence_score=0.95  # OpenRouter doesn't provide confidence scores
            )
            
            # Mark as completed
            result.mark_completed(translated_text, metrics)
            
            self.logger.info(
                "Translation completed successfully",
                request_id=request.request_id,
                model=model_name,
                input_length=len(request.text),
                output_length=len(translated_text),
                processing_time_ms=processing_time
            )
            
            return result
            
        except Exception as e:
            # Create error object
            if isinstance(e, HTTPError):
                if e.status_code == 429:
                    error_type = ErrorType.RATE_LIMIT_ERROR
                elif e.status_code == 401:
                    error_type = ErrorType.AUTHENTICATION_ERROR
                elif e.status_code and e.status_code >= 500:
                    error_type = ErrorType.PROVIDER_ERROR
                else:
                    error_type = ErrorType.VALIDATION_ERROR
            else:
                error_type = ErrorType.UNKNOWN_ERROR
            
            error = TranslationError(
                error_type=error_type,
                message=str(e),
                is_retryable=getattr(e, 'is_retryable', False)
            )
            
            result.mark_failed(error)
            
            self.logger.error(
                "Translation failed",
                request_id=request.request_id,
                error=str(e),
                error_type=error_type.value
            )
            
            return result
    
    async def _perform_translation(self, request: TranslationRequest, model_name: str) -> str:
        """Perform the actual translation API call"""
        
        async def make_request():
            # Get API key
            key_info = await self.key_manager.get_available_key(self.config.name)
            if not key_info:
                raise Exception("No available API keys")
            
            api_key = self.key_manager.get_api_key(key_info.key_id)
            if not api_key:
                raise Exception("Failed to retrieve API key")
            
            try:
                # Create prompt for translation
                prompt = self._create_translation_prompt(request)
                
                # Prepare API request
                payload = {
                    "model": model_name,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 4000,
                    "stream": False
                }
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://ai-translation-framework.com",
                    "X-Title": "AI Translation Framework"
                }
                
                # Make API call with tracing
                with self.tracer.trace_provider_call(self.name, model_name, request.request_id):
                    response = await self.http_client.post(
                        url=f"{self.config.base_url}/chat/completions",
                        json_data=payload,
                        headers=headers,
                        timeout=self.config.timeout_seconds
                    )
                
                # Parse response
                response_data = response.json()
                
                if "choices" not in response_data or not response_data["choices"]:
                    raise Exception("Invalid API response: no choices returned")
                
                translated_text = response_data["choices"][0]["message"]["content"].strip()
                
                # Report success
                await self.key_manager.report_key_success(
                    key_info.key_id,
                    tokens_used=response_data.get("usage", {}).get("total_tokens")
                )
                
                return translated_text
                
            except HTTPError as e:
                # Report key error based on HTTP status
                if e.status_code == 429:
                    await self.key_manager.report_key_error(key_info.key_id, "rate_limit")
                elif e.status_code == 401:
                    await self.key_manager.report_key_error(key_info.key_id, "invalid_key")
                else:
                    await self.key_manager.report_key_error(key_info.key_id, "api_error")
                raise
                
            except Exception as e:
                # Report generic error
                await self.key_manager.report_key_error(key_info.key_id, "unknown_error")
                raise
        
        # Execute with retry logic
        return await self.retry_handler.execute_with_retry(
            make_request,
            operation_name="openrouter_translation",
            custom_retry_condition=self.retry_handler.create_provider_retry_condition()
        )
    
    def _create_translation_prompt(self, request: TranslationRequest) -> str:
        """Create translation prompt for the AI model"""
        
        # Map language codes to full names
        language_names = {
            "vi": "Vietnamese",
            "en": "English", 
            "ja": "Japanese",
            "ko": "Korean",
            "zh-CN": "Simplified Chinese",
            "zh-TW": "Traditional Chinese",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ar": "Arabic"
        }
        
        target_lang = language_names.get(request.target_language, request.target_language)
        source_lang = language_names.get(request.source_language, "the source language") if request.source_language != "auto" else "the source language"
        
        # Style-specific instructions
        style_instructions = {
            "formal": "Use formal, polite language appropriate for business or academic contexts.",
            "casual": "Use casual, conversational language as if talking to a friend.",
            "literary": "Use eloquent, literary language with attention to style and flow.",
            "technical": "Use precise technical terminology and maintain accuracy of technical concepts.",
            "conversational": "Use natural, conversational language that sounds native.",
            "game_dialogue": "Use dynamic, engaging language suitable for game characters and dialogue.",
            "subtitle": "Use concise, clear language suitable for subtitles (keep it brief)."
        }
        
        style_instruction = style_instructions.get(request.style, style_instructions["conversational"])
        
        prompt = f"""Please translate the following text from {source_lang} to {target_lang}.

Translation Style: {style_instruction}

{f'Additional Context: {request.context}' if request.context else ''}
{f'Custom Instructions: {request.custom_instructions}' if request.custom_instructions else ''}

Text to translate:
{request.text}

Please provide only the translation without any explanations or additional text."""
        
        return prompt
    
    async def translate_streaming(self, request: TranslationRequest) -> AsyncIterator[str]:
        """
        Translate with streaming response (not implemented for OpenRouter yet).
        
        Args:
            request: Translation request
            
        Yields:
            Partial translation strings
            
        Raises:
            NotImplementedError: Streaming not yet implemented
        """
        raise NotImplementedError("Streaming translation not yet implemented for OpenRouter")
    
    async def health_check(self) -> bool:
        """
        Check if OpenRouter API is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Get an available key
            key_info = await self.key_manager.get_available_key(self.config.name)
            if not key_info:
                return False
            
            api_key = self.key_manager.get_api_key(key_info.key_id)
            if not api_key:
                return False
            
            # Make a simple API call to check health
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Use a minimal request for health check
            payload = {
                "model": self.config.default_model or "anthropic/claude-3-haiku",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 5
            }
            
            response = await self.http_client.post(
                url=f"{self.config.base_url}/chat/completions",
                json_data=payload,
                headers=headers,
                timeout=10  # Short timeout for health check
            )
            
            return response.is_success
            
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return False
    
    async def get_available_models(self) -> List[str]:
        """
        Get list of available models.
        
        Returns:
            List of model names
        """
        return [model.name for model in self.config.models]
    
    async def estimate_cost(self, request: TranslationRequest) -> Optional[float]:
        """
        Estimate cost for translation request.
        
        Args:
            request: Translation request
            
        Returns:
            Estimated cost in USD or None if not available
        """
        model_config = self.config.get_model(request.model_name)
        if not model_config or not model_config.input_cost_per_1k_tokens:
            return None
        
        # Rough token estimation (1 token ≈ 4 characters for English, varies for other languages)
        estimated_input_tokens = len(request.text) / 4
        estimated_output_tokens = estimated_input_tokens * 1.2  # Assume output is 20% longer
        
        input_cost = (estimated_input_tokens / 1000) * model_config.input_cost_per_1k_tokens
        output_cost = 0
        
        if model_config.output_cost_per_1k_tokens:
            output_cost = (estimated_output_tokens / 1000) * model_config.output_cost_per_1k_tokens
        
        return input_cost + output_cost
    
    async def close(self) -> None:
        """Close provider and clean up resources"""
        await self.http_client.close()
        self.logger.info("OpenRouter provider closed")


class FakeOpenRouterProvider(OpenRouterProvider):
    """
    Fake OpenRouter provider for testing without API keys.
    
    Returns mock responses instead of making real API calls.
    """
    
    def __init__(self, config: ProviderConfig, key_manager: InMemoryKeyManager):
        super().__init__(config, key_manager)
        self.logger.info("Using FAKE OpenRouter provider for testing")
    
    async def _perform_translation(self, request: TranslationRequest, model_name: str) -> str:
        """Return a fake translation response"""
        import asyncio
        
        # Simulate API delay
        await asyncio.sleep(0.5)
        
        # Create fake translation based on target language
        fake_translations = {
            "vi": f"[FAKE VIETNAMESE TRANSLATION] {request.text}",
            "en": f"[FAKE ENGLISH TRANSLATION] {request.text}",
            "ja": f"[FAKE JAPANESE TRANSLATION] {request.text}",
            "ko": f"[FAKE KOREAN TRANSLATION] {request.text}",
            "zh-CN": f"[FAKE CHINESE TRANSLATION] {request.text}",
            "es": f"[FAKE SPANISH TRANSLATION] {request.text}",
            "fr": f"[FAKE FRENCH TRANSLATION] {request.text}",
        }
        
        fake_translation = fake_translations.get(
            request.target_language, 
            f"[FAKE {request.target_language.upper()} TRANSLATION] {request.text}"
        )
        
        self.logger.info(
            "Generated fake translation",
            request_id=request.request_id,
            model=model_name,
            input_length=len(request.text),
            output_length=len(fake_translation)
        )
        
        return fake_translation
    
    async def health_check(self) -> bool:
        """Always return healthy for fake provider"""
        return True


def create_openrouter_provider(config: ProviderConfig, use_fake: bool = False) -> OpenRouterProvider:
    """
    Factory function to create OpenRouter provider.
    
    Args:
        config: Provider configuration
        use_fake: Whether to use fake provider for testing
        
    Returns:
        OpenRouter provider instance
    """
    # Create key manager
    key_manager = InMemoryKeyManager()
    
    if use_fake or not config.api_keys:
        return FakeOpenRouterProvider(config, key_manager)
    else:
        return OpenRouterProvider(config, key_manager)