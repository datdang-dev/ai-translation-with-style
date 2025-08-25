"""Core translation service with orchestration"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from ..interfaces import TranslationProvider
from ..models import (
    TranslationRequest, TranslationResult, BatchTranslationRequest, 
    BatchTranslationResult, TranslationStatus, TranslationError, ErrorType
)
from .provider_registry import ProviderRegistry, ProviderNotFoundError
from ...infrastructure.observability import get_logger, get_metrics, get_tracer


class TranslationService:
    """
    Core translation service that orchestrates translation requests.
    
    Features:
    - Single and batch translation
    - Provider selection and fallback
    - Concurrent processing with rate limiting
    - Comprehensive error handling and recovery
    - Observability and metrics
    """
    
    def __init__(
        self, 
        provider_registry: ProviderRegistry,
        max_concurrent_requests: int = 10,
        enable_fallback: bool = True
    ):
        """
        Initialize translation service.
        
        Args:
            provider_registry: Registry of available providers
            max_concurrent_requests: Maximum concurrent translation requests
            enable_fallback: Whether to enable provider fallback
        """
        self.provider_registry = provider_registry
        self.max_concurrent_requests = max_concurrent_requests
        self.enable_fallback = enable_fallback
        
        # Concurrency control
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # Observability
        self.logger = get_logger("translation_service")
        self.metrics = get_metrics()
        self.tracer = get_tracer()
    
    async def translate_single(
        self, 
        request: TranslationRequest,
        preferred_provider: Optional[str] = None
    ) -> TranslationResult:
        """
        Translate a single request using batch processing internally.
        
        Note: The new architecture always uses batch processing for consistency
        and optimal resource utilization, even for single requests.
        
        Args:
            request: Translation request
            preferred_provider: Optional preferred provider name
            
        Returns:
            Translation result
        """
        self.logger.info(
            "Starting single translation (using batch processing internally)",
            request_id=request.request_id,
            source_lang=request.source_language,
            target_lang=request.target_language,
            text_length=len(request.text),
            preferred_provider=preferred_provider
        )
        
        # Create a single-item batch request
        batch_request = BatchTranslationRequest(
            requests=[request],
            max_concurrent=1,
            shared_provider=preferred_provider,
            batch_timeout_seconds=request.timeout_seconds or 30
        )
        
        # Process as batch
        batch_result = await self.translate_batch(batch_request)
        
        # Return the single result
        if batch_result.results:
            return batch_result.results[0]
        else:
            # Fallback error result
            return TranslationResult(
                request_id=request.request_id,
                status=TranslationStatus.FAILED,
                original_text=request.text,
                target_language=request.target_language,
                error=TranslationError(
                    error_type=ErrorType.UNKNOWN_ERROR,
                    message="Batch processing returned no results",
                    is_retryable=False
                )
            )
    
    async def translate_batch(
        self, 
        batch_request: BatchTranslationRequest
    ) -> BatchTranslationResult:
        """
        Translate a batch of requests concurrently.
        
        Args:
            batch_request: Batch translation request
            
        Returns:
            Batch translation result
        """
        self.logger.info(
            "Starting batch translation",
            batch_id=batch_request.batch_id,
            batch_size=len(batch_request.requests),
            max_concurrent=batch_request.max_concurrent,
            fail_fast=batch_request.fail_fast
        )
        
        # Apply shared settings to individual requests
        batch_request.apply_shared_settings()
        
        # Create batch result
        batch_result = BatchTranslationResult(
            batch_id=batch_request.batch_id,
            total_requests=len(batch_request.requests),
            started_at=datetime.now(timezone.utc)
        )
        
        # Create semaphore for batch concurrency control
        batch_semaphore = asyncio.Semaphore(batch_request.max_concurrent)
        
        async def translate_single_with_semaphore(req: TranslationRequest) -> TranslationResult:
            async with batch_semaphore:
                return await self._translate_with_fallback(req, batch_request.shared_provider)
        
        try:
            # Process requests concurrently
            with self.tracer.trace_batch_processing(
                batch_request.batch_id, 
                len(batch_request.requests),
                batch_request.shared_provider or "auto"
            ):
                if batch_request.fail_fast:
                    # Fail fast: stop on first error
                    results = await self._process_batch_fail_fast(
                        batch_request.requests, 
                        translate_single_with_semaphore
                    )
                else:
                    # Process all requests regardless of failures
                    tasks = [
                        translate_single_with_semaphore(req) 
                        for req in batch_request.requests
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Create error result for exception
                    request = batch_request.requests[i]
                    error_result = TranslationResult(
                        request_id=request.request_id,
                        status=TranslationStatus.FAILED,
                        original_text=request.text,
                        target_language=request.target_language,
                        error=TranslationError(
                            error_type=ErrorType.UNKNOWN_ERROR,
                            message=str(result),
                            is_retryable=False
                        )
                    )
                    batch_result.add_result(error_result)
                else:
                    batch_result.add_result(result)
            
            batch_result.completed_at = datetime.now(timezone.utc)
            
            self.logger.info(
                "Batch translation completed",
                batch_id=batch_request.batch_id,
                total_requests=batch_result.total_requests,
                successful_requests=batch_result.successful_requests,
                failed_requests=batch_result.failed_requests,
                success_rate=batch_result.success_rate,
                processing_time_ms=batch_result.total_processing_time_ms
            )
            
            return batch_result
            
        except Exception as e:
            batch_result.completed_at = datetime.now(timezone.utc)
            
            self.logger.error(
                "Batch translation failed",
                batch_id=batch_request.batch_id,
                error=str(e)
            )
            
            raise
    
    async def _translate_with_fallback(
        self, 
        request: TranslationRequest,
        preferred_provider: Optional[str] = None
    ) -> TranslationResult:
        """
        Translate with provider fallback logic.
        
        Args:
            request: Translation request
            preferred_provider: Preferred provider name
            
        Returns:
            Translation result
        """
        providers_tried = []
        last_error = None
        
        try:
            # Try preferred provider first
            if preferred_provider:
                try:
                    provider = await self.provider_registry.get_provider(preferred_provider)
                    providers_tried.append(preferred_provider)
                    
                    self.logger.debug(
                        "Trying preferred provider",
                        request_id=request.request_id,
                        provider=preferred_provider
                    )
                    
                    result = await provider.translate(request)
                    
                    if result.is_success:
                        self.metrics.record_translation_request(
                            provider=preferred_provider,
                            model=result.metrics.model_name if result.metrics else "unknown",
                            status="success",
                            duration_seconds=(result.metrics.processing_time_ms or 0) / 1000.0
                        )
                        return result
                    else:
                        last_error = result.error
                        
                except ProviderNotFoundError as e:
                    last_error = e
                    self.logger.warning(
                        "Preferred provider not available",
                        request_id=request.request_id,
                        provider=preferred_provider,
                        error=str(e)
                    )
            
            # Try default provider if no preferred provider or it failed
            if not preferred_provider or self.enable_fallback:
                try:
                    provider = await self.provider_registry.get_default_provider()
                    provider_name = provider.name
                    
                    if provider_name not in providers_tried:
                        providers_tried.append(provider_name)
                        
                        self.logger.debug(
                            "Trying default provider",
                            request_id=request.request_id,
                            provider=provider_name
                        )
                        
                        result = await provider.translate(request)
                        
                        if result.is_success:
                            self.metrics.record_translation_request(
                                provider=provider_name,
                                model=result.metrics.model_name if result.metrics else "unknown",
                                status="success",
                                duration_seconds=(result.metrics.processing_time_ms or 0) / 1000.0
                            )
                            return result
                        else:
                            last_error = result.error
                            
                except ProviderNotFoundError as e:
                    last_error = e
                    self.logger.warning(
                        "Default provider not available",
                        request_id=request.request_id,
                        error=str(e)
                    )
            
            # Try fallback providers if enabled
            if self.enable_fallback:
                fallback_providers = await self.provider_registry.get_fallback_providers(
                    exclude=preferred_provider
                )
                
                for provider in fallback_providers:
                    if provider.name in providers_tried:
                        continue
                    
                    providers_tried.append(provider.name)
                    
                    try:
                        self.logger.debug(
                            "Trying fallback provider",
                            request_id=request.request_id,
                            provider=provider.name
                        )
                        
                        result = await provider.translate(request)
                        
                        if result.is_success:
                            self.metrics.record_translation_request(
                                provider=provider.name,
                                model=result.metrics.model_name if result.metrics else "unknown",
                                status="success",
                                duration_seconds=(result.metrics.processing_time_ms or 0) / 1000.0
                            )
                            
                            self.logger.info(
                                "Translation succeeded with fallback provider",
                                request_id=request.request_id,
                                provider=provider.name,
                                providers_tried=providers_tried
                            )
                            
                            return result
                        else:
                            last_error = result.error
                            
                    except Exception as e:
                        last_error = e
                        self.logger.warning(
                            "Fallback provider failed",
                            request_id=request.request_id,
                            provider=provider.name,
                            error=str(e)
                        )
            
            # All providers failed
            self.logger.error(
                "All providers failed",
                request_id=request.request_id,
                providers_tried=providers_tried,
                last_error=str(last_error) if last_error else "Unknown error"
            )
            
            # Record failure metrics
            for provider_name in providers_tried:
                self.metrics.record_translation_request(
                    provider=provider_name,
                    model="unknown",
                    status="error",
                    duration_seconds=0
                )
            
            # Create failure result
            error = TranslationError(
                error_type=ErrorType.PROVIDER_ERROR,
                message=f"All providers failed. Tried: {', '.join(providers_tried)}. Last error: {last_error}",
                is_retryable=True
            )
            
            result = TranslationResult(
                request_id=request.request_id,
                status=TranslationStatus.FAILED,
                original_text=request.text,
                target_language=request.target_language,
                error=error
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Unexpected error in translation",
                request_id=request.request_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            error = TranslationError(
                error_type=ErrorType.UNKNOWN_ERROR,
                message=str(e),
                is_retryable=False
            )
            
            result = TranslationResult(
                request_id=request.request_id,
                status=TranslationStatus.FAILED,
                original_text=request.text,
                target_language=request.target_language,
                error=error
            )
            
            return result
    
    async def _process_batch_fail_fast(
        self, 
        requests: List[TranslationRequest],
        translate_func
    ) -> List[TranslationResult]:
        """Process batch with fail-fast behavior"""
        results = []
        
        for request in requests:
            try:
                result = await translate_func(request)
                results.append(result)
                
                # Stop on first failure
                if result.is_failed:
                    self.logger.warning(
                        "Batch processing stopped due to failure (fail-fast mode)",
                        request_id=request.request_id,
                        processed_count=len(results),
                        total_count=len(requests)
                    )
                    break
                    
            except Exception as e:
                self.logger.error(
                    "Batch processing stopped due to exception (fail-fast mode)",
                    request_id=request.request_id,
                    error=str(e),
                    processed_count=len(results),
                    total_count=len(requests)
                )
                results.append(e)
                break
        
        return results
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        provider_info = self.provider_registry.get_provider_info()
        health_status = await self.provider_registry.run_health_checks()
        
        return {
            "providers": provider_info,
            "health_status": health_status,
            "max_concurrent_requests": self.max_concurrent_requests,
            "enable_fallback": self.enable_fallback,
            "active_requests": self.max_concurrent_requests - self.semaphore._value
        }
    
    async def close(self) -> None:
        """Close service and clean up resources"""
        await self.provider_registry.close_all_providers()
        self.logger.info("Translation service closed")