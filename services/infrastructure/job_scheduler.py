"""
Job Scheduler with queue management and delay mechanism
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from services.common.logger import get_logger


class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Job definition"""
    job_id: str
    task: Callable
    args: tuple = ()
    kwargs: dict = None
    priority: int = 0  # Lower number = higher priority
    delay: float = 0.0  # Delay before execution in seconds
    created_at: float = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}
        if self.created_at is None:
            self.created_at = time.time()


class JobScheduler:
    """Job scheduler with queue management and concurrency control"""
    
    def __init__(self, max_concurrent: int = 3, default_delay: float = 0.0):
        self.max_concurrent = max_concurrent
        self.default_delay = default_delay
        self.logger = get_logger("JobScheduler")
        
        # Job tracking
        self.jobs: Dict[str, Job] = {}
        self.pending_queue: List[str] = []  # Job IDs waiting to be executed
        self.running_jobs: Dict[str, asyncio.Task] = {}  # Currently running jobs
        self.completed_jobs: List[str] = []  # Completed job IDs
        
        # Control flags
        self._shutdown = False
        self._scheduler_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'cancelled_jobs': 0,
            'total_processing_time': 0.0
        }
    
    async def start(self):
        """Start the job scheduler"""
        if self._scheduler_task is None or self._scheduler_task.done():
            self._shutdown = False
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            self.logger.info("Job scheduler started")
    
    async def stop(self):
        """Stop the job scheduler"""
        self._shutdown = True
        
        # Cancel running jobs
        for job_id, task in self.running_jobs.items():
            task.cancel()
            self.jobs[job_id].status = JobStatus.CANCELLED
            self.stats['cancelled_jobs'] += 1
        
        # Wait for scheduler to stop
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Job scheduler stopped")
    
    def add_job(self, job_id: str, task: Callable, *args, 
                priority: int = 0, delay: float = None, **kwargs) -> Job:
        """Add a job to the queue"""
        if job_id in self.jobs:
            raise ValueError(f"Job {job_id} already exists")
        
        job = Job(
            job_id=job_id,
            task=task,
            args=args,
            kwargs=kwargs,
            priority=priority,
            delay=delay if delay is not None else self.default_delay
        )
        
        self.jobs[job_id] = job
        self.pending_queue.append(job_id)
        self.stats['total_jobs'] += 1
        
        # Sort queue by priority (lower number = higher priority)
        self.pending_queue.sort(key=lambda jid: self.jobs[jid].priority)
        
        self.logger.info(f"📋 Job {job_id} added to queue (priority: {priority}, delay: {job.delay}s)")
        self._log_queue_status()
        
        return job
    
    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get status of a specific job"""
        job = self.jobs.get(job_id)
        return job.status if job else None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            'pending_jobs': len(self.pending_queue),
            'running_jobs': len(self.running_jobs),
            'completed_jobs': len(self.completed_jobs),
            'total_jobs': len(self.jobs),
            'max_concurrent': self.max_concurrent,
            'is_running': not self._shutdown,
            'pending_job_ids': self.pending_queue.copy(),
            'running_job_ids': list(self.running_jobs.keys())
        }
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status of all jobs"""
        status_by_category = {
            'pending': [],
            'waiting': [],
            'running': [],
            'completed': [],
            'failed': [],
            'cancelled': []
        }
        
        for job_id, job in self.jobs.items():
            job_info = {
                'job_id': job_id,
                'priority': job.priority,
                'delay': job.delay,
                'created_at': job.created_at,
                'started_at': job.started_at,
                'completed_at': job.completed_at,
                'duration': (job.completed_at - job.started_at) if (job.started_at and job.completed_at) else None
            }
            
            status_by_category[job.status.value].append(job_info)
        
        return {
            'summary': self.get_queue_status(),
            'statistics': self.stats.copy(),
            'jobs_by_status': status_by_category
        }
    
    async def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all jobs to complete"""
        start_time = time.time()
        
        while (self.pending_queue or self.running_jobs) and not self._shutdown:
            if timeout and (time.time() - start_time) > timeout:
                self.logger.warning(f"Wait timeout after {timeout}s")
                return False
            
            await asyncio.sleep(0.1)
        
        return True
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        self.logger.info("🚀 Job scheduler loop started")
        
        try:
            while not self._shutdown:
                await self._process_queue()
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
        except asyncio.CancelledError:
            self.logger.info("Job scheduler loop cancelled")
        except Exception as e:
            self.logger.error(f"Job scheduler loop error: {e}")
        finally:
            self.logger.info("Job scheduler loop ended")
    
    async def _process_queue(self):
        """Process pending jobs based on concurrency limits"""
        # Clean up completed tasks
        completed_tasks = []
        for job_id, task in self.running_jobs.items():
            if task.done():
                completed_tasks.append(job_id)
        
        for job_id in completed_tasks:
            await self._handle_completed_job(job_id)
        
        # Start new jobs if we have capacity
        available_slots = self.max_concurrent - len(self.running_jobs)
        
        if available_slots > 0 and self.pending_queue:
            jobs_to_start = []
            current_time = time.time()
            
            # Find jobs that are ready to run (delay has passed)
            for job_id in self.pending_queue[:available_slots]:
                job = self.jobs[job_id]
                wait_time = job.created_at + job.delay - current_time
                
                if wait_time <= 0:
                    # Job is ready to run
                    jobs_to_start.append(job_id)
                else:
                    # Job is still waiting
                    job.status = JobStatus.WAITING
                    self.logger.debug(f"⏳ Job {job_id} waiting {wait_time:.1f}s more")
            
            # Start ready jobs
            for job_id in jobs_to_start:
                await self._start_job(job_id)
    
    async def _start_job(self, job_id: str):
        """Start a specific job"""
        job = self.jobs[job_id]
        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        
        # Remove from pending queue
        self.pending_queue.remove(job_id)
        
        # Create and start task
        task = asyncio.create_task(self._execute_job(job))
        self.running_jobs[job_id] = task
        
        self.logger.info(f"🏃 Job {job_id} started")
        self._log_queue_status()
    
    async def _execute_job(self, job: Job) -> Any:
        """Execute a job"""
        try:
            if asyncio.iscoroutinefunction(job.task):
                result = await job.task(*job.args, **job.kwargs)
            else:
                result = job.task(*job.args, **job.kwargs)
            
            job.result = result
            job.status = JobStatus.COMPLETED
            job.completed_at = time.time()
            
            return result
            
        except Exception as e:
            job.error = e
            job.status = JobStatus.FAILED
            job.completed_at = time.time()
            self.logger.error(f"❌ Job {job.job_id} failed: {e}")
            raise
    
    async def _handle_completed_job(self, job_id: str):
        """Handle a completed job"""
        task = self.running_jobs.pop(job_id)
        job = self.jobs[job_id]
        
        try:
            # Get result (this will raise if job failed)
            result = await task
            
            if job.status == JobStatus.COMPLETED:
                self.completed_jobs.append(job_id)
                self.stats['completed_jobs'] += 1
                self.stats['total_processing_time'] += (job.completed_at - job.started_at)
                self.logger.info(f"✅ Job {job_id} completed successfully")
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = e
            self.stats['failed_jobs'] += 1
            self.logger.error(f"❌ Job {job_id} failed: {e}")
        
        self._log_queue_status()
    
    def _log_queue_status(self):
        """Log current queue status"""
        status = self.get_queue_status()
        self.logger.info(
            f"📊 Queue Status: "
            f"Pending={status['pending_jobs']}, "
            f"Running={status['running_jobs']}, "
            f"Completed={status['completed_jobs']}"
        )
        
        if status['pending_job_ids']:
            pending_jobs = [f"{jid}(p:{self.jobs[jid].priority})" for jid in status['pending_job_ids'][:3]]
            if len(status['pending_job_ids']) > 3:
                pending_jobs.append("...")
            self.logger.info(f"📋 Pending Jobs: {', '.join(pending_jobs)}")
        
        if status['running_job_ids']:
            self.logger.info(f"🏃 Running Jobs: {', '.join(status['running_job_ids'])}")
    
    def update_max_concurrent(self, max_concurrent: int):
        """Update max concurrent jobs"""
        old_value = self.max_concurrent
        self.max_concurrent = max_concurrent
        self.logger.info(f"Updated max concurrent from {old_value} to {max_concurrent}")