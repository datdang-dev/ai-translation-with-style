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
from services.infrastructure.job_scheduler import JobScheduler, JobStatus
from services.common.logger import get_logger


class TranslationManager:
    """Main translation manager for orchestrating batch operations"""
    
    def __init__(self, 
                 request_manager: RequestManager = None,
                 resiliency_manager: ResiliencyManager = None,
                 batch_size: int = 10,
                 max_concurrent: int = 3,
                 job_delay: float = 0.0):
        
        self.request_manager = request_manager or RequestManager()
        self.resiliency_manager = resiliency_manager or ResiliencyManager()
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.job_delay = job_delay
        
        # Initialize job scheduler
        self.job_scheduler = JobScheduler(
            max_concurrent=max_concurrent,
            default_delay=job_delay
        )
        
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
                # Create a wrapper function that matches the expected signature
                async def process_request_wrapper(*args, **kwargs):
                    return await self.request_manager.process_request(request)
                
                return await self.resiliency_manager.execute_with_retry(
                    process_request_wrapper,
                    "request_manager"
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
    
    async def translate_text_batch(self, 
                                 content_list: List[str], 
                                 target_lang: str,
                                 source_lang: str = "auto") -> BatchResult:
        """Convenience method for TEXT batch translation"""
        requests = []
        
        for i, content in enumerate(content_list):
            request = TranslationRequest(
                content=content,
                source_lang=source_lang,
                target_lang=target_lang,
                format_type=FormatType.TEXT,
                request_id=f"text_batch_{i}"
            )
            requests.append(request)
        
        return await self._process_batch_with_result(requests, "text_batch")
    
    async def process_batch(self, requests: List[TranslationRequest]) -> List[TranslationResult]:
        """Process a batch of translation requests using job scheduler"""
        self.logger.info(f"🚀 Processing batch of {len(requests)} requests with job scheduler")
        
        # Start job scheduler if not running
        await self.job_scheduler.start()
        
        # Create jobs for each request
        job_ids = []
        for i, request in enumerate(requests):
            job_id = f"translation_job_{request.request_id}_{i}"
            priority = i  # Sequential priority
            delay = i * self.job_delay  # Stagger jobs by delay
            
            self.job_scheduler.add_job(
                job_id,
                self._process_single_request,
                request,  # Pass request as argument
                priority=priority,
                delay=delay
            )
            job_ids.append(job_id)
            
            self.logger.info(f"📋 Job {job_id} queued (priority: {priority}, delay: {delay:.1f}s)")
        
        # Log initial queue status
        self._log_detailed_queue_status()
        
        # Wait for all jobs to complete
        await self.job_scheduler.wait_for_completion()
        
        # Collect results
        results = []
        for job_id in job_ids:
            job = self.job_scheduler.jobs[job_id]
            if job.status == JobStatus.COMPLETED:
                results.append(job.result)
                self.logger.info(f"✅ Job {job_id} completed successfully")
            else:
                # Create error result
                error_result = TranslationResult(
                    original="",
                    translated="",
                    provider="unknown",
                    validation_passed=False,
                    validation_details={"error": str(job.error) if job.error else "Job failed"},
                    request_id=job_id
                )
                results.append(error_result)
                self.logger.error(f"❌ Job {job_id} failed: {job.error}")
        
        # Log final statistics
        self._log_batch_completion_stats(job_ids)
        
        # Stop job scheduler
        await self.job_scheduler.stop()
        
        return results
    
    async def _process_single_request(self, request: TranslationRequest) -> TranslationResult:
        """Process a single translation request"""
        self.logger.info(f"🔄 Processing request {request.request_id}")
        
        start_time = time.time()
        
        # Create a wrapper function that matches the expected signature
        async def process_request_wrapper(*args, **kwargs):
            return await self.request_manager.process_request(request)
        
        # Use resiliency manager for the actual translation
        result = await self.resiliency_manager.execute_with_retry(
            func=process_request_wrapper,
            provider="request_manager"
        )
        
        processing_time = time.time() - start_time
        result.processing_time = processing_time
        
        self.logger.info(f"✅ Request {request.request_id} completed in {processing_time:.2f}s")
        
        return result
    
    def _log_detailed_queue_status(self):
        """Log detailed queue status with job information"""
        status = self.job_scheduler.get_detailed_status()
        
        self.logger.info(f"📊 QUEUE STATUS OVERVIEW:")
        self.logger.info(f"   Pending: {len(status['jobs_by_status']['pending'])}")
        self.logger.info(f"   Waiting: {len(status['jobs_by_status']['waiting'])}")  
        self.logger.info(f"   Running: {len(status['jobs_by_status']['running'])}")
        self.logger.info(f"   Completed: {len(status['jobs_by_status']['completed'])}")
        
        # Log pending jobs with details
        if status['jobs_by_status']['pending']:
            self.logger.info("📋 PENDING JOBS:")
            for job in status['jobs_by_status']['pending'][:5]:  # Show first 5
                self.logger.info(f"   - {job['job_id']} (priority: {job['priority']}, delay: {job['delay']:.1f}s)")
        
        # Log waiting jobs
        if status['jobs_by_status']['waiting']:
            self.logger.info("⏳ WAITING JOBS:")
            for job in status['jobs_by_status']['waiting'][:3]:  # Show first 3
                self.logger.info(f"   - {job['job_id']} (waiting for delay)")
        
        # Log running jobs
        if status['jobs_by_status']['running']:
            self.logger.info("🏃 RUNNING JOBS:")
            for job in status['jobs_by_status']['running']:
                duration = time.time() - job['started_at'] if job['started_at'] else 0
                self.logger.info(f"   - {job['job_id']} (running for {duration:.1f}s)")
    
    def _log_batch_completion_stats(self, job_ids: List[str]):
        """Log batch completion statistics"""
        status = self.job_scheduler.get_detailed_status()
        
        completed = len(status['jobs_by_status']['completed'])
        failed = len(status['jobs_by_status']['failed'])
        total = len(job_ids)
        
        self.logger.info(f"📊 BATCH COMPLETION SUMMARY:")
        self.logger.info(f"   Total Jobs: {total}")
        self.logger.info(f"   Completed: {completed}")
        self.logger.info(f"   Failed: {failed}")
        self.logger.info(f"   Success Rate: {(completed/total*100):.1f}%" if total > 0 else "N/A")
        
        if status['statistics']['total_processing_time'] > 0:
            avg_time = status['statistics']['total_processing_time'] / completed if completed > 0 else 0
            self.logger.info(f"   Average Processing Time: {avg_time:.2f}s")
    
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
    
    def update_configuration(self, max_concurrent: int = None, job_delay: float = None):
        """Update configuration parameters"""
        if max_concurrent is not None:
            old_concurrent = self.max_concurrent
            self.max_concurrent = max_concurrent
            self.semaphore = asyncio.Semaphore(max_concurrent)
            self.job_scheduler.update_max_concurrent(max_concurrent)
            self.logger.info(f"Updated max_concurrent from {old_concurrent} to {max_concurrent}")
        
        if job_delay is not None:
            old_delay = self.job_delay
            self.job_delay = job_delay
            self.logger.info(f"Updated job_delay from {old_delay} to {job_delay}")
    
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
                           max_concurrent: int = None,
                           job_delay: float = None):
        """Update manager configuration"""
        if batch_size is not None:
            self.batch_size = batch_size
            self.logger.info(f"Updated batch size to {batch_size}")
        
        if max_concurrent is not None:
            old_concurrent = self.max_concurrent
            self.max_concurrent = max_concurrent
            self.semaphore = asyncio.Semaphore(max_concurrent)
            self.job_scheduler.update_max_concurrent(max_concurrent)
            self.logger.info(f"Updated max concurrent from {old_concurrent} to {max_concurrent}")
        
        if job_delay is not None:
            old_delay = self.job_delay
            self.job_delay = job_delay
            self.logger.info(f"Updated job_delay from {old_delay} to {job_delay}")
    
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
