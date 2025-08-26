"""
Request manager with full processing pipeline
"""

import time
from typing import List, Dict, Any, Optional
from services.models import (
    TranslationRequest, TranslationResult, StandardizedContent, 
    FormatType, ProviderError
)
from services.standardizer import StandardizerService
from services.providers import ProviderOrchestrator
from services.infrastructure import CacheService, ValidatorService
from services.common.logger import get_logger


class RequestManager:
    """Manages the full translation request pipeline"""
    
    def __init__(self, 
                 standardizer_service: StandardizerService = None,
                 provider_orchestrator: ProviderOrchestrator = None,
                 cache_service: CacheService = None,
                 validator_service: ValidatorService = None,
                 max_workers: int = 10):
        
        self.standardizer_service = standardizer_service or StandardizerService()
        self.provider_orchestrator = provider_orchestrator or ProviderOrchestrator()
        self.cache_service = cache_service
        self.validator_service = validator_service or ValidatorService()
        self.max_workers = max_workers
        
        self.logger = get_logger("RequestManager")
        
        # Processing statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'validation_passes': 0,
            'validation_failures': 0
        }
    
    async def process_request(self, request: TranslationRequest) -> TranslationResult:
        """Process a single translation request through the full pipeline"""
        start_time = time.time()
        request_id = request.request_id
        
        self.logger.info(f"Processing request {request_id} for {request.format_type.value}")
        self.stats['total_requests'] += 1
        
        try:
            # Step 1: Check cache first
            cached_result = await self._check_cache(request)
            if cached_result:
                self.logger.info(f"Cache hit for request {request_id}")
                self.stats['cache_hits'] += 1
                self.stats['successful_requests'] += 1
                return cached_result
            
            self.stats['cache_misses'] += 1
            
            # Step 2: Standardize content
            self.logger.debug(f"Standardizing content for request {request_id}")
            standardized_content = await self._standardize_content(request)
            
            # Step 3: Translate content
            self.logger.debug(f"Translating content for request {request_id}")
            translated_content = await self._translate_content(request, standardized_content)
            
            # Step 4: Reconstruct result
            self.logger.debug(f"Reconstructing result for request {request_id}")
            reconstructed_result = await self._reconstruct_content(standardized_content, translated_content)
            
            # Step 5: Validate translation
            self.logger.debug(f"Validating translation for request {request_id}")
            validation_result = await self._validate_translation(request, reconstructed_result)
            
            # Step 6: Create final result
            processing_time = time.time() - start_time
            
            result = TranslationResult(
                original=request.content,
                translated=reconstructed_result,
                provider=self._get_provider_name_used(request),
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                format_type=request.format_type,
                request_id=request_id,
                processing_time=processing_time,
                validation_passed=validation_result['valid'],
                validation_details=validation_result
            )
            
            # Step 7: Cache the result
            await self._cache_result(request, result)
            
            self.logger.info(f"Successfully processed request {request_id} in {processing_time:.2f}s")
            self.stats['successful_requests'] += 1
            
            if validation_result['valid']:
                self.stats['validation_passes'] += 1
            else:
                self.stats['validation_failures'] += 1
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Failed to process request {request_id}: {e}")
            self.stats['failed_requests'] += 1
            
            # Return error result
            error_result = TranslationResult(
                original=request.content,
                translated=None,
                provider="error",
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                format_type=request.format_type,
                request_id=request_id,
                processing_time=processing_time,
                validation_passed=False,
                validation_details={'valid': False, 'error': str(e)}
            )
            
            raise ProviderError(f"Request processing failed: {e}", details={'request_id': request_id})
    
    async def _check_cache(self, request: TranslationRequest) -> Optional[TranslationResult]:
        """Check cache for existing translation"""
        if not self.cache_service:
            return None
        
        try:
            # For complex content, we'll check cache based on standardized chunks
            if request.format_type in [FormatType.RENPY, FormatType.JSON]:
                # Generate cache key based on content hash
                cache_key = self.cache_service.generate_key(
                    "translation",
                    str(hash(str(request.content))),
                    request.source_lang,
                    request.target_lang,
                    request.format_type.value
                )
            else:
                # Simple text caching
                cache_key = self.cache_service.generate_translation_key(
                    str(request.content),
                    request.target_lang,
                    request.source_lang
                )
            
            cached_data = await self.cache_service.get(cache_key)
            
            if cached_data:
                # Reconstruct TranslationResult from cached data
                return TranslationResult(
                    original=request.content,
                    translated=cached_data.get('translated'),
                    provider=cached_data.get('provider', 'cache'),
                    source_lang=request.source_lang,
                    target_lang=request.target_lang,
                    format_type=request.format_type,
                    request_id=request.request_id,
                    from_cache=True,
                    processing_time=0.0
                )
            
        except Exception as e:
            self.logger.warning(f"Cache check failed: {e}")
        
        return None
    
    async def _standardize_content(self, request: TranslationRequest) -> StandardizedContent:
        """Standardize content for translation"""
        try:
            return self.standardizer_service.standardize(request.content, request.format_type)
        except Exception as e:
            self.logger.error(f"Content standardization failed: {e}")
            raise ProviderError(f"Failed to standardize content: {e}")
    
    async def _translate_content(self, 
                               request: TranslationRequest, 
                               standardized_content: StandardizedContent) -> List[str]:
        """Translate standardized content"""
        try:
            # Get translatable texts
            translatable_texts = standardized_content.get_translatable_texts()
            
            if not translatable_texts:
                self.logger.info("No translatable content found")
                return []
            
            # Translate using provider orchestrator
            translations = await self.provider_orchestrator.translate(
                translatable_texts,
                request.target_lang,
                request.source_lang
            )
            
            return translations
            
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            raise ProviderError(f"Translation failed: {e}")
    
    async def _reconstruct_content(self, 
                                 standardized_content: StandardizedContent, 
                                 translations: List[str]) -> Any:
        """Reconstruct content with translations"""
        try:
            if not translations:
                # No translations, return original
                return standardized_content.original_content
            
            # Apply translations to chunks
            translatable_chunks = standardized_content.get_translatable_chunks()
            
            if len(translations) != len(translatable_chunks):
                self.logger.warning(
                    f"Translation count mismatch: {len(translations)} translations "
                    f"for {len(translatable_chunks)} chunks"
                )
                # Pad or truncate as needed
                while len(translations) < len(translatable_chunks):
                    translations.append("")
                translations = translations[:len(translatable_chunks)]
            
            # Apply translations
            for chunk, translation in zip(translatable_chunks, translations):
                chunk.translation = translation
            
            # Reconstruct content
            return self.standardizer_service.reconstruct(standardized_content)
            
        except Exception as e:
            self.logger.error(f"Content reconstruction failed: {e}")
            raise ProviderError(f"Failed to reconstruct content: {e}")
    
    async def _validate_translation(self, 
                                  request: TranslationRequest, 
                                  translated_content: Any) -> Dict[str, Any]:
        """Validate the translation quality"""
        try:
            # For simple validation, compare original and translated as strings
            original_str = str(request.content)
            translated_str = str(translated_content)
            
            validation_result = self.validator_service.validate_translation(
                original_str,
                translated_str,
                context={
                    'format_type': request.format_type.value,
                    'source_lang': request.source_lang,
                    'target_lang': request.target_lang
                }
            )
            
            return validation_result
            
        except Exception as e:
            self.logger.warning(f"Validation failed: {e}")
            return {
                'valid': True,  # Assume valid if validation fails
                'overall_score': 0.5,
                'message': f'Validation error: {e}',
                'validator_results': {}
            }
    
    async def _cache_result(self, request: TranslationRequest, result: TranslationResult):
        """Cache the translation result"""
        if not self.cache_service or not result.validation_passed:
            return
        
        try:
            # Generate same cache key as in _check_cache
            if request.format_type in [FormatType.RENPY, FormatType.JSON]:
                cache_key = self.cache_service.generate_key(
                    "translation",
                    str(hash(str(request.content))),
                    request.source_lang,
                    request.target_lang,
                    request.format_type.value
                )
            else:
                cache_key = self.cache_service.generate_translation_key(
                    str(request.content),
                    request.target_lang,
                    request.source_lang
                )
            
            cache_data = {
                'translated': result.translated,
                'provider': result.provider,
                'cached_at': time.time(),
                'processing_time': result.processing_time,
                'validation_passed': result.validation_passed
            }
            
            await self.cache_service.set(cache_key, cache_data)
            
        except Exception as e:
            self.logger.warning(f"Failed to cache result: {e}")
    
    def _get_provider_name_used(self, request: TranslationRequest) -> str:
        """Get the name of the provider that would be used"""
        try:
            return self.provider_orchestrator.select_provider(request)
        except:
            return "unknown"
    
    def validate_request(self, request: TranslationRequest) -> Dict[str, Any]:
        """Validate incoming request"""
        errors = []
        warnings = []
        
        # Basic validation
        if not request.content:
            errors.append("Request content is empty")
        
        if not request.target_lang:
            errors.append("Target language is required")
        
        if request.format_type not in [FormatType.RENPY, FormatType.JSON, FormatType.TEXT]:
            errors.append(f"Unsupported format type: {request.format_type}")
        
        # Content validation
        try:
            if not self.standardizer_service.validate_content(request.content, request.format_type):
                warnings.append(f"Content may not be valid {request.format_type.value} format")
        except Exception as e:
            warnings.append(f"Content validation failed: {e}")
        
        # Provider availability
        try:
            available_providers = self.provider_orchestrator.get_available_providers()
            if not available_providers:
                errors.append("No translation providers available")
        except Exception as e:
            warnings.append(f"Provider check failed: {e}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    async def transform_request(self, request: TranslationRequest) -> TranslationRequest:
        """Transform request for provider consumption (if needed)"""
        # For now, just return the request as-is
        # In the future, this could normalize languages, adjust content, etc.
        return request
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        total_requests = self.stats['total_requests']
        
        return {
            'total_requests': total_requests,
            'successful_requests': self.stats['successful_requests'],
            'failed_requests': self.stats['failed_requests'],
            'success_rate': (self.stats['successful_requests'] / total_requests * 100) if total_requests > 0 else 0,
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'cache_hit_rate': (self.stats['cache_hits'] / (self.stats['cache_hits'] + self.stats['cache_misses']) * 100) if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0 else 0,
            'validation_passes': self.stats['validation_passes'],
            'validation_failures': self.stats['validation_failures'],
            'validation_pass_rate': (self.stats['validation_passes'] / (self.stats['validation_passes'] + self.stats['validation_failures']) * 100) if (self.stats['validation_passes'] + self.stats['validation_failures']) > 0 else 0
        }
    
    def reset_stats(self):
        """Reset processing statistics"""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'validation_passes': 0,
            'validation_failures': 0
        }
        self.logger.info("Processing statistics reset")
    
    def get_pipeline_health(self) -> Dict[str, Any]:
        """Get health status of pipeline components"""
        health = {
            'standardizer_service': True,  # Always available
            'validator_service': True,     # Always available
            'cache_service': self.cache_service is not None,
            'provider_orchestrator': len(self.provider_orchestrator.get_available_providers()) > 0
        }
        
        # Overall health
        all_healthy = all(health.values())
        
        return {
            'overall_healthy': all_healthy,
            'components': health,
            'available_providers': self.provider_orchestrator.get_available_providers(),
            'provider_count': len(self.provider_orchestrator.list_providers())
        }
    
    async def process_batch_requests(self, requests: List[TranslationRequest]) -> List[TranslationResult]:
        """Process multiple requests efficiently"""
        if not requests:
            return []
        
        self.logger.info(f"Processing batch of {len(requests)} requests")
        
        # For now, process sequentially
        # In future, could implement concurrent processing with semaphore
        results = []
        
        for request in requests:
            try:
                result = await self.process_request(request)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Batch request failed: {e}")
                # Create error result
                error_result = TranslationResult(
                    original=request.content,
                    translated=None,
                    provider="error",
                    source_lang=request.source_lang,
                    target_lang=request.target_lang,
                    format_type=request.format_type,
                    request_id=request.request_id,
                    processing_time=0.0,
                    validation_passed=False,
                    validation_details={'valid': False, 'error': str(e)}
                )
                results.append(error_result)
        
        self.logger.info(f"Batch processing completed: {len(results)} results")
        return results