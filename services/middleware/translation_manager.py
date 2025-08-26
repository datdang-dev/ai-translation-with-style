"""
Translation manager for batch processing and orchestration
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from services.models import (
    TranslationRequest, TranslationResult, BatchResult, 
    FormatType, ProviderType
)
from services.middleware.request_manager import RequestManager
from services.resiliency import ResiliencyManager
from services.common.logger import get_logger


class TranslationManager:
    """Main translation manager for orchestrating batch operations"""
    
    def __init__(self, 
                 request_manager: RequestManager = None,
                 resiliency_manager: ResiliencyManager = None,
                 batch_size: int = 10,
                 max_concurrent: int = 3):
        
        self.request_manager = request_manager or RequestManager()
        self.resiliency_manager = resiliency_manager or ResiliencyManager()
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        
        self.logger = get_logger("TranslationManager")
        
        # Concurrency control
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Processing statistics
        self.batch_stats = {
            'total_batches': 0,
            'successful_batches': 0,
            'failed_batches': 0,
            'total_requests_processed': 0,
            'total_processing_time': 0.0
        }
    
    async def process_batch(self, requests: List[TranslationRequest]) -> List[TranslationResult]:
        """Process a batch of translation requests"""
        if not requests:
            return []
        
        batch_id = f"batch_{int(time.time())}_{len(requests)}"
        self.logger.info(f"Processing batch {batch_id} with {len(requests)} requests")
        
        start_time = time.time()
        self.batch_stats['total_batches'] += 1
        
        try:
            # Process requests with concurrency control
            if len(requests) <= self.max_concurrent:
                # Small batch - process all concurrently
                results = await self._process_concurrent_batch(requests)
            else:
                # Large batch - process in chunks
                results = await self._process_chunked_batch(requests)
            
            processing_time = time.time() - start_time
            self.batch_stats['successful_batches'] += 1
            self.batch_stats['total_requests_processed'] += len(requests)
            self.batch_stats['total_processing_time'] += processing_time
            
            self.logger.info(
                f"Batch {batch_id} completed successfully in {processing_time:.2f}s. "
                f"Success rate: {self._calculate_success_rate(results):.1%}"
            )
            
            return results
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.batch_stats['failed_batches'] += 1
            self.logger.error(f"Batch {batch_id} failed after {processing_time:.2f}s: {e}")
            
            # Return error results for all requests
            error_results = []
            for request in requests:
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
                error_results.append(error_result)
            
            return error_results
    
    async def _process_concurrent_batch(self, requests: List[TranslationRequest]) -> List[TranslationResult]:
        """Process requests concurrently"""
        async def process_with_semaphore(request):
            async with self.semaphore:
                return await self.resiliency_manager.execute_with_retry(
                    self.request_manager.process_request,
                    "request_manager",
                    request
                )
        
        tasks = [process_with_semaphore(request) for request in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = TranslationResult(
                    original=requests[i].content,
                    translated=None,
                    provider="error",
                    source_lang=requests[i].source_lang,
                    target_lang=requests[i].target_lang,
                    format_type=requests[i].format_type,
                    request_id=requests[i].request_id,
                    processing_time=0.0,
                    validation_passed=False,
                    validation_details={'valid': False, 'error': str(result)}
                )
                final_results.append(error_result)
            else:
                final_results.append(result)
        
        return final_results
    
    async def _process_chunked_batch(self, requests: List[TranslationRequest]) -> List[TranslationResult]:
        """Process large batch in chunks"""
        all_results = []
        
        for i in range(0, len(requests), self.batch_size):
            chunk = requests[i:i + self.batch_size]
            chunk_results = await self._process_concurrent_batch(chunk)
            all_results.extend(chunk_results)
            
            # Brief pause between chunks to avoid overwhelming providers
            if i + self.batch_size < len(requests):
                await asyncio.sleep(0.1)
        
        return all_results
    
    def _calculate_success_rate(self, results: List[TranslationResult]) -> float:
        """Calculate success rate for batch results"""
        if not results:
            return 0.0
        
        successful = sum(1 for result in results if result.validation_passed)
        return successful / len(results)
    
    async def translate_renpy_batch(self, 
                                  content_list: List[str], 
                                  target_lang: str,
                                  source_lang: str = "auto") -> BatchResult:
        """Convenience method for Renpy batch translation"""
        requests = []
        
        for i, content in enumerate(content_list):
            request = TranslationRequest(
                content=content,
                source_lang=source_lang,
                target_lang=target_lang,
                format_type=FormatType.RENPY,
                request_id=f"renpy_batch_{i}"
            )
            requests.append(request)
        
        return await self._process_batch_with_result(requests, "renpy_batch")
    
    async def translate_json_batch(self, 
                                 content_list: List[Any], 
                                 target_lang: str,
                                 source_lang: str = "auto") -> BatchResult:
        """Convenience method for JSON batch translation"""
        requests = []
        
        for i, content in enumerate(content_list):
            request = TranslationRequest(
                content=content,
                source_lang=source_lang,
                target_lang=target_lang,
                format_type=FormatType.JSON,
                request_id=f"json_batch_{i}"
            )
            requests.append(request)
        
        return await self._process_batch_with_result(requests, "json_batch")
    
    async def _process_batch_with_result(self, 
                                       requests: List[TranslationRequest], 
                                       batch_type: str) -> BatchResult:
        """Process batch and return structured result"""
        start_time = time.time()
        
        # Process the batch
        results = await self.process_batch(requests)
        
        # Analyze results
        successful_translations = sum(1 for result in results if result.validation_passed)
        failed_translations = len(results) - successful_translations
        
        # Calculate metrics
        total_processing_time = time.time() - start_time
        average_processing_time = (
            sum(result.processing_time for result in results) / len(results)
            if results else 0.0
        )
        
        # Calculate cache hit rate
        cache_hits = sum(1 for result in results if result.from_cache)
        cache_hit_rate = cache_hits / len(results) if results else 0.0
        
        # Collect errors
        errors = []
        for result in results:
            if not result.validation_passed:
                errors.append({
                    'request_id': result.request_id,
                    'error': result.validation_details.get('error', 'Unknown error'),
                    'provider': result.provider
                })
        
        batch_result = BatchResult(
            total_requests=len(requests),
            successful_translations=successful_translations,
            failed_translations=failed_translations,
            results=results,
            errors=errors,
            total_processing_time=total_processing_time,
            average_processing_time=average_processing_time,
            cache_hit_rate=cache_hit_rate * 100,  # Convert to percentage
            batch_id=f"{batch_type}_{int(start_time)}"
        )
        
        batch_result.mark_completed()
        
        self.logger.info(
            f"Batch {batch_type} completed: {successful_translations}/{len(requests)} successful "
            f"({batch_result.success_rate:.1f}% success rate)"
        )
        
        return batch_result
    
    def get_status(self) -> Dict[str, Any]:
        """Get current manager status"""
        pipeline_health = self.request_manager.get_pipeline_health()
        processing_stats = self.request_manager.get_processing_stats()
        
        return {
            'healthy': pipeline_health['overall_healthy'],
            'pipeline_health': pipeline_health,
            'processing_stats': processing_stats,
            'batch_stats': self.batch_stats,
            'configuration': {
                'batch_size': self.batch_size,
                'max_concurrent': self.max_concurrent
            },
            'available_providers': pipeline_health['available_providers']
        }
    
    async def shutdown(self):
        """Gracefully shutdown manager"""
        self.logger.info("Shutting down translation manager")
        
        # Wait for current operations to complete
        # In a real implementation, you might want to track active tasks
        await asyncio.sleep(0.1)
        
        self.logger.info("Translation manager shutdown complete")
    
    def update_configuration(self, 
                           batch_size: int = None,
                           max_concurrent: int = None):
        """Update manager configuration"""
        if batch_size is not None:
            self.batch_size = batch_size
            self.logger.info(f"Updated batch size to {batch_size}")
        
        if max_concurrent is not None:
            self.max_concurrent = max_concurrent
            self.semaphore = asyncio.Semaphore(max_concurrent)
            self.logger.info(f"Updated max concurrent to {max_concurrent}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        total_batches = self.batch_stats['total_batches']
        total_requests = self.batch_stats['total_requests_processed']
        total_time = self.batch_stats['total_processing_time']
        
        metrics = {
            'batch_metrics': {
                'total_batches': total_batches,
                'successful_batches': self.batch_stats['successful_batches'],
                'failed_batches': self.batch_stats['failed_batches'],
                'batch_success_rate': (self.batch_stats['successful_batches'] / total_batches * 100) if total_batches > 0 else 0,
                'average_batch_time': total_time / total_batches if total_batches > 0 else 0
            },
            'request_metrics': {
                'total_requests_processed': total_requests,
                'average_requests_per_batch': total_requests / total_batches if total_batches > 0 else 0,
                'requests_per_second': total_requests / total_time if total_time > 0 else 0
            },
            'configuration': {
                'batch_size': self.batch_size,
                'max_concurrent': self.max_concurrent
            }
        }
        
        # Add request manager metrics
        request_stats = self.request_manager.get_processing_stats()
        metrics['request_manager_stats'] = request_stats
        
        return metrics
    
    def reset_statistics(self):
        """Reset all statistics"""
        self.batch_stats = {
            'total_batches': 0,
            'successful_batches': 0,
            'failed_batches': 0,
            'total_requests_processed': 0,
            'total_processing_time': 0.0
        }
        
        self.request_manager.reset_stats()
        self.logger.info("All statistics reset")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        health_results = {
            'translation_manager': True,
            'request_manager': True,
            'resiliency_manager': True
        }
        
        # Check pipeline health
        pipeline_health = self.request_manager.get_pipeline_health()
        health_results.update({
            'pipeline_overall': pipeline_health['overall_healthy'],
            'standardizer_service': pipeline_health['components']['standardizer_service'],
            'cache_service': pipeline_health['components']['cache_service'],
            'validator_service': pipeline_health['components']['validator_service'],
            'provider_orchestrator': pipeline_health['components']['provider_orchestrator']
        })
        
        # Overall health
        overall_healthy = all(health_results.values())
        
        return {
            'healthy': overall_healthy,
            'components': health_results,
            'available_providers': pipeline_health['available_providers'],
            'provider_count': pipeline_health['provider_count'],
            'last_check': time.time()
        }