"""
Base provider interface and common functionality
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from services.models import TranslationRequest, TranslationResult, HealthStatus, ProviderStats, ProviderError


class ITranslationProvider(ABC):
    """Interface for translation providers"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Get provider name"""
        pass
    
    @abstractmethod
    async def translate(self, texts: List[str], target_lang: str, source_lang: str = "auto") -> List[str]:
        """Translate list of texts"""
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check provider health"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Get provider capabilities"""
        pass
    
    @abstractmethod
    def get_rate_limits(self) -> Dict[str, int]:
        """Get provider rate limits"""
        pass


class BaseTranslationProvider(ITranslationProvider):
    """Base implementation with common functionality"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.stats = ProviderStats(name=name)
        self._enabled = self.config.get('enabled', True)
        self._priority = self.config.get('priority', 1)
    
    def get_name(self) -> str:
        return self.name
    
    def is_enabled(self) -> bool:
        """Check if provider is enabled"""
        return self._enabled
    
    def get_priority(self) -> int:
        """Get provider priority (lower = higher priority)"""
        return self._priority
    
    def get_stats(self) -> ProviderStats:
        """Get provider statistics"""
        return self.stats
    
    async def translate_request(self, request: TranslationRequest) -> TranslationResult:
        """Translate a full request object"""
        import time
        start_time = time.time()
        
        try:
            # Extract translatable text based on format
            if hasattr(request, 'translatable_texts'):
                texts = request.translatable_texts
            else:
                # Fallback to simple string conversion
                texts = [str(request.content)] if request.content else []
            
            if not texts:
                # No translatable content
                return TranslationResult(
                    original=request.content,
                    translated=request.content,
                    provider=self.get_name(),
                    source_lang=request.source_lang,
                    target_lang=request.target_lang,
                    format_type=request.format_type,
                    request_id=request.request_id,
                    processing_time=0.0
                )
            
            # Perform translation
            translated_texts = await self.translate(texts, request.target_lang, request.source_lang)
            
            processing_time = time.time() - start_time
            
            # Record successful request
            self.stats.record_request(True, processing_time)
            
            return TranslationResult(
                original=request.content,
                translated=translated_texts,
                provider=self.get_name(),
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                format_type=request.format_type,
                request_id=request.request_id,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.stats.record_request(False, processing_time)
            raise ProviderError(f"Translation failed: {e}", details={'provider': self.get_name()})
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Default capabilities"""
        return {
            'max_text_length': self.config.get('max_text_length', 5000),
            'max_batch_size': self.config.get('max_batch_size', 100),
            'supported_languages': self.config.get('supported_languages', []),
            'supports_auto_detect': self.config.get('supports_auto_detect', True)
        }
    
    def get_rate_limits(self) -> Dict[str, int]:
        """Default rate limits"""
        return {
            'requests_per_minute': self.config.get('requests_per_minute', 60),
            'requests_per_hour': self.config.get('requests_per_hour', 1000),
            'characters_per_minute': self.config.get('characters_per_minute', 50000)
        }
    
    async def health_check(self) -> HealthStatus:
        """Basic health check implementation"""
        try:
            # Simple translation test
            test_result = await self.translate(["Hello"], "es", "en")
            if test_result and len(test_result) > 0:
                return HealthStatus.healthy(f"{self.get_name()} is operational")
            else:
                return HealthStatus.unhealthy(f"{self.get_name()} returned empty result")
        except Exception as e:
            return HealthStatus.unhealthy(f"{self.get_name()} health check failed: {e}")
    
    def _validate_texts(self, texts: List[str]) -> None:
        """Validate input texts"""
        if not texts:
            raise ProviderError("No texts provided for translation")
        
        capabilities = self.get_capabilities()
        max_batch_size = capabilities.get('max_batch_size', 100)
        max_text_length = capabilities.get('max_text_length', 5000)
        
        if len(texts) > max_batch_size:
            raise ProviderError(f"Batch size {len(texts)} exceeds limit {max_batch_size}")
        
        for i, text in enumerate(texts):
            if len(text) > max_text_length:
                raise ProviderError(f"Text {i} length {len(text)} exceeds limit {max_text_length}")
    
    def _validate_languages(self, source_lang: str, target_lang: str) -> None:
        """Validate language codes"""
        capabilities = self.get_capabilities()
        supported_languages = capabilities.get('supported_languages', [])
        
        if supported_languages:
            if target_lang not in supported_languages:
                raise ProviderError(f"Target language '{target_lang}' not supported")
            
            if source_lang != "auto" and source_lang not in supported_languages:
                raise ProviderError(f"Source language '{source_lang}' not supported")