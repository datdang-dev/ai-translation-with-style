"""
Batch Translation Orchestrator
Handles concurrent translation of multiple files
"""

import asyncio
import json
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from services.common.logger import get_logger
from applet.orchestrator import TranslationOrchestrator

@dataclass
class BatchJob:
    """Represents a single translation job"""
    input_path: str
    output_path: str
    status: str = "pending"  # pending, processing, completed, failed
    error: str = None
    start_time: float = None
    end_time: float = None
    result: Dict[str, Any] = None
    # Use monotonic clock for reliable duration calculations
    start_monotonic: float = None
    end_monotonic: float = None

class BatchTranslationOrchestrator:
    """Handles batch translation of multiple files"""
    
    def __init__(self, config_path: str, max_concurrent: int = 3, job_delay: float = 10.0):
        """
        Initialize batch orchestrator
        :param config_path: Path to configuration file
        :param max_concurrent: Maximum concurrent translations
        :param job_delay: Delay in seconds between jobs to avoid rate limiting
        """
        self.config_path = config_path
        self.max_concurrent = max_concurrent
        self.job_delay = job_delay
        self.logger = get_logger("BatchTranslationOrchestrator")
        self.jobs: List[BatchJob] = []
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    def add_job(self, input_path: str, output_path: str) -> None:
        """Add a translation job to the batch"""
        job = BatchJob(input_path=input_path, output_path=output_path)
        self.jobs.append(job)
        self.logger.info(f"Added job: {input_path} -> {output_path}")
    
    def add_jobs_from_directory(self, input_dir: str, output_dir: str, pattern: str = "*.json") -> None:
        """Add all matching files from directory as jobs in numerical order"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Find all matching files and sort them numerically
        file_paths = list(input_path.glob(pattern))
        # Sort files numerically by extracting number from filename
        import re
        def extract_number(filename):
            # Extract number from filename (e.g., chunk_001.json -> 1)
            match = re.search(r'(\d+)', filename)
            return int(match.group(1)) if match else 0
        
        file_paths.sort(key=lambda x: extract_number(x.name))
        
        # Add jobs in sorted order
        for file_path in file_paths:
            if file_path.is_file():
                output_file = output_path / file_path.name
                self.add_job(str(file_path), str(output_file))
        
        self.logger.info(f"Added {len([j for j in self.jobs if j.input_path.startswith(str(input_path))])} jobs from directory in numerical order")
    
    async def _process_single_job(self, job: BatchJob) -> None:
        """Process a single translation job"""
        async with self.semaphore:  # Limit concurrent executions
            try:
                job.status = "processing"
                # Record both wall-clock (for human-readable timestamps) and
                # monotonic time (for accurate duration calculations)
                job.start_time = time.time()
                job.start_monotonic = time.monotonic()
                
                self.logger.info(f"🔄 [PROCESSING] Job started at {time.strftime('%H:%M:%S', time.localtime(job.start_time))}")
                self.logger.info(f"   ├── File: {job.input_path}")
                self.logger.info(f"   └── PID: {os.getpid()}")
                
                # Create orchestrator for this job
                orchestrator = TranslationOrchestrator(self.config_path)
                
                # Translate the file
                success = await orchestrator.translate_file(job.input_path, job.output_path)
                
                job.end_time = time.time()
                job.end_monotonic = time.monotonic()
                
                if success:
                    job.status = "completed"
                    # Load result for reporting
                    with open(job.output_path, 'r', encoding='utf-8') as f:
                        job.result = json.load(f)
                    duration_s = (job.end_monotonic - job.start_monotonic) if (job.end_monotonic is not None and job.start_monotonic is not None) else None
                    if duration_s is not None:
                        self.logger.info(f"✅ [SUCCESS] Job completed at {time.strftime('%H:%M:%S', time.localtime(job.end_time))} (duration: {duration_s:.2f}s)")
                    else:
                        self.logger.info(f"✅ [SUCCESS] Job completed at {time.strftime('%H:%M:%S', time.localtime(job.end_time))}")
                else:
                    job.status = "failed"
                    job.error = "Translation failed"
                    duration_s = (job.end_monotonic - job.start_monotonic) if (job.end_monotonic is not None and job.start_monotonic is not None) else None
                    if duration_s is not None:
                        self.logger.error(f"❌ [FAILED] Job failed at {time.strftime('%H:%M:%S', time.localtime(job.end_time))} (duration: {duration_s:.2f}s)")
                    else:
                        self.logger.error(f"❌ [FAILED] Job failed at {time.strftime('%H:%M:%S', time.localtime(job.end_time))}")
                    
            except Exception as e:
                job.status = "failed"
                job.error = str(e)
                job.end_time = time.time()
                job.end_monotonic = time.monotonic()
                duration_s = (job.end_monotonic - job.start_monotonic) if (job.end_monotonic is not None and job.start_monotonic is not None) else None
                if duration_s is not None:
                    self.logger.error(f"💥 [ERROR] Job failed at {time.strftime('%H:%M:%S', time.localtime(job.end_time))}: {e} (duration: {duration_s:.2f}s)")
                else:
                    self.logger.error(f"💥 [ERROR] Job failed at {time.strftime('%H:%M:%S', time.localtime(job.end_time))}: {e}")
                # Log full exception details
                import traceback
                self.logger.error(f"📋 [TRACEBACK] Full traceback: {traceback.format_exc()}")
                # Log the actual exception type and details
                self.logger.error(f"🔍 [EXCEPTION] Type: {type(e).__name__}")
                if hasattr(e, '__dict__'):
                    self.logger.error(f"📊 [DETAILS] Exception attributes: {e.__dict__}")
    
    async def process_all_jobs(self) -> Dict[str, Any]:
        """Process all jobs sequentially with delay between jobs"""
        if not self.jobs:
            self.logger.warning("No jobs to process")
            return {
                "status": "no_jobs",
                "total_jobs": 0,
                "completed": 0,
                "failed": 0,
                "pending": 0,
                "total_time": 0,
                "average_time_per_job": 0,
                "success_rate": 0,
                "jobs": []
            }
        
        self.logger.info(f"🚀 Starting batch processing of {len(self.jobs)} jobs with {self.job_delay}s delay between jobs")
        self.logger.info(f"📋 Jobs to process:")
        for i, job in enumerate(self.jobs, 1):
            self.logger.info(f"   {i}. {job.input_path}")
        start_time = time.time()
        run_start_monotonic = time.monotonic()
        
        # Process jobs with delay between job starts
        tasks = []
        for i, job in enumerate(self.jobs):
            # Log job start with timestamp
            start_timestamp = time.time()
            self.logger.info(f"🚀 [JOB {i+1}/{len(self.jobs)}] STARTING at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_timestamp))}")
            self.logger.info(f"   ├── File: {job.input_path}")
            self.logger.info(f"   ├── Delay to next job: {self.job_delay}s")
            self.logger.info(f"   └── Max concurrent: {self.max_concurrent}")
            
            # Start the job (don't wait for completion)
            task = asyncio.create_task(self._process_single_job(job))
            tasks.append(task)
            
            # Add delay before next job starts (except for the last job)
            if i < len(self.jobs) - 1:
                delay_start_wall = time.time()
                delay_start_monotonic = time.monotonic()
                self.logger.info(f"⏳ [JOB {i+2}/{len(self.jobs)}] WAITING for {self.job_delay}s delay (started at {time.strftime('%H:%M:%S', time.localtime(delay_start_wall))})")
                await asyncio.sleep(self.job_delay)
                delay_end_wall = time.time()
                delay_end_monotonic = time.monotonic()
                delay_duration = delay_end_monotonic - delay_start_monotonic
                self.logger.info(f"   └── Delay completed at {time.strftime('%H:%M:%S', time.localtime(delay_end_wall))} (duration: {delay_duration:.2f}s)")
            else:
                self.logger.info(f"🏁 ALL JOBS STARTED - Waiting for completions...")
        
        # Wait for all jobs to complete
        self.logger.info(f"⏳ Waiting for all {len(tasks)} jobs to complete...")
        await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        run_end_monotonic = time.monotonic()
        
        # Log job completions summary
        completed_jobs = [j for j in self.jobs if j.status == "completed"]
        failed_jobs = [j for j in self.jobs if j.status == "failed"]
        
        self.logger.info(f"📊 JOB COMPLETION SUMMARY:")
        self.logger.info(f"   ├── Completed: {len(completed_jobs)}/{len(self.jobs)}")
        self.logger.info(f"   ├── Failed: {len(failed_jobs)}/{len(self.jobs)}")
        self.logger.info(f"   └── Total duration: {run_end_monotonic - run_start_monotonic:.2f}s")
        
        # Log individual job completions
        for i, job in enumerate(self.jobs):
            if job.end_time:
                duration = (job.end_monotonic - job.start_monotonic) if (job.end_monotonic is not None and job.start_monotonic is not None) else None
                if job.status == "completed":
                    if duration is not None:
                        self.logger.info(f"✅ [JOB {i+1}/{len(self.jobs)}] COMPLETED at {time.strftime('%H:%M:%S', time.localtime(job.end_time))} (duration: {duration:.2f}s)")
                    else:
                        self.logger.info(f"✅ [JOB {i+1}/{len(self.jobs)}] COMPLETED at {time.strftime('%H:%M:%S', time.localtime(job.end_time))}")
                    self.logger.info(f"   ├── File: {job.input_path}")
                    self.logger.info(f"   └── Status: SUCCESS")
                else:
                    if duration is not None:
                        self.logger.info(f"❌ [JOB {i+1}/{len(self.jobs)}] FAILED at {time.strftime('%H:%M:%S', time.localtime(job.end_time))} (duration: {duration:.2f}s)")
                    else:
                        self.logger.info(f"❌ [JOB {i+1}/{len(self.jobs)}] FAILED at {time.strftime('%H:%M:%S', time.localtime(job.end_time))}")
                    self.logger.info(f"   ├── File: {job.input_path}")
                    self.logger.info(f"   └── Error: {job.error}")
        
        # Generate summary
        total_duration = run_end_monotonic - run_start_monotonic
        summary = self._generate_summary(total_duration)
        
        self.logger.info(f"🎯 Batch processing completed in {total_duration:.2f}s")
        self.logger.info(f"📊 Summary: {summary['completed']} completed, {summary['failed']} failed")
        
        # Log failed jobs details
        if summary['failed'] > 0:
            self.logger.error(f"❌ Failed jobs:")
            for job in summary['jobs']:
                if job['status'] == 'failed':
                    self.logger.error(f"   - {job['input_path']}: {job['error']}")
        
        return summary
    
    def _generate_summary(self, total_duration: float) -> Dict[str, Any]:
        """Generate processing summary using monotonic total duration"""
        completed = [j for j in self.jobs if j.status == "completed"]
        failed = [j for j in self.jobs if j.status == "failed"]
        pending = [j for j in self.jobs if j.status == "pending"]
        
        total_time = total_duration
        avg_time = total_time / len(self.jobs) if self.jobs else 0
        
        return {
            "total_jobs": len(self.jobs),
            "completed": len(completed),
            "failed": len(failed),
            "pending": len(pending),
            "total_time": total_time,
            "average_time_per_job": avg_time,
            "success_rate": len(completed) / len(self.jobs) if self.jobs else 0,
            "jobs": [
                {
                    "input_path": job.input_path,
                    "output_path": job.output_path,
                    "status": job.status,
                    "error": job.error,
                    "processing_time": (job.end_monotonic - job.start_monotonic) if (job.end_monotonic is not None and job.start_monotonic is not None) else None,
                    "result_keys": len(job.result) if job.result else 0
                }
                for job in self.jobs
            ]
        }
    
    def get_job_status(self, input_path: str) -> BatchJob:
        """Get status of a specific job"""
        for job in self.jobs:
            if job.input_path == input_path:
                return job
        return None
    
    def clear_jobs(self) -> None:
        """Clear all jobs"""
        self.jobs.clear()
        self.logger.info("Cleared all jobs")

# Utility function for batch processing
async def run_batch_translation(
    config_path: str,
    input_files: List[str],
    output_files: List[str],
    max_concurrent: int = 3,
    job_delay: float = 10.0
) -> Dict[str, Any]:
    """
    Utility function to run batch translation
    :param config_path: Configuration file path
    :param input_files: List of input file paths
    :param output_files: List of output file paths
    :param max_concurrent: Maximum concurrent translations
    :return: Processing summary
    """
    if len(input_files) != len(output_files):
        raise ValueError("Input and output file lists must have the same length")
    
    orchestrator = BatchTranslationOrchestrator(config_path, max_concurrent, job_delay)
    
    # Add jobs
    for input_file, output_file in zip(input_files, output_files):
        orchestrator.add_job(input_file, output_file)
    
    # Process all jobs
    return await orchestrator.process_all_jobs()

# Utility function for directory-based batch processing
async def run_batch_translation_from_directory(
    config_path: str,
    input_dir: str,
    output_dir: str,
    pattern: str = "*.json",
    max_concurrent: int = 3,
    job_delay: float = 10.0
) -> Dict[str, Any]:
    """
    Utility function to run batch translation from directory
    :param config_path: Configuration file path
    :param input_dir: Input directory path
    :param output_dir: Output directory path
    :param pattern: File pattern to match
    :param max_concurrent: Maximum concurrent translations
    :return: Processing summary
    """
    orchestrator = BatchTranslationOrchestrator(config_path, max_concurrent, job_delay)
    
    # Add jobs from directory
    orchestrator.add_jobs_from_directory(input_dir, output_dir, pattern)
    
    # Process all jobs
    return await orchestrator.process_all_jobs()
