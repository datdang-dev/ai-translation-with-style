"""
Job Scheduler
Handles timer-based job scheduling with configurable intervals
"""

import asyncio
import time
from typing import List, Dict, Any, Callable, Awaitable
from dataclasses import dataclass
from services.common.logger import get_logger

@dataclass
class ScheduledJob:
    """Represents a scheduled job"""
    id: str
    task: Callable[[], Awaitable[Any]]
    interval: float  # seconds between executions
    last_run: float = 0
    next_run: float = 0
    is_running: bool = False
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    last_error: str = None

class JobScheduler:
    """Timer-based job scheduler that runs jobs at fixed intervals"""
    
    def __init__(self, default_interval: float = 10.0):
        """
        Initialize job scheduler
        :param default_interval: Default interval between job executions in seconds
        """
        self.default_interval = default_interval
        self.jobs: Dict[str, ScheduledJob] = {}
        self.running = False
        self.logger = get_logger("JobScheduler")
        self._task = None
    
    def add_job(self, job_id: str, task: Callable[[], Awaitable[Any]], 
                interval: float = None) -> None:
        """
        Add a job to the scheduler
        :param job_id: Unique identifier for the job
        :param task: Async function to execute
        :param interval: Interval between executions (uses default if None)
        """
        if interval is None:
            interval = self.default_interval
        
        now = time.time()
        job = ScheduledJob(
            id=job_id,
            task=task,
            interval=interval,
            next_run=now + interval
        )
        
        self.jobs[job_id] = job
        self.logger.info(f"Added job '{job_id}' with {interval}s interval")
    
    def remove_job(self, job_id: str) -> bool:
        """
        Remove a job from the scheduler
        :param job_id: Job identifier to remove
        :return: True if job was found and removed, False otherwise
        """
        if job_id in self.jobs:
            del self.jobs[job_id]
            self.logger.info(f"Removed job '{job_id}'")
            return True
        return False
    
    def update_job_interval(self, job_id: str, new_interval: float) -> bool:
        """
        Update the interval for a specific job
        :param job_id: Job identifier
        :param new_interval: New interval in seconds
        :return: True if job was found and updated, False otherwise
        """
        if job_id in self.jobs:
            self.jobs[job_id].interval = new_interval
            # Recalculate next run time
            now = time.time()
            self.jobs[job_id].next_run = now + new_interval
            self.logger.info(f"Updated job '{job_id}' interval to {new_interval}s")
            return True
        return False
    
    async def start(self) -> None:
        """Start the job scheduler"""
        if self.running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.logger.info(f"Starting job scheduler with {len(self.jobs)} jobs")
        
        # Start the main scheduling loop
        self._task = asyncio.create_task(self._scheduler_loop())
    
    async def stop(self) -> None:
        """Stop the job scheduler"""
        if not self.running:
            return
        
        self.running = False
        self.logger.info("Stopping job scheduler")
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
    
    async def _scheduler_loop(self) -> None:
        """Main scheduling loop that runs jobs at their scheduled times"""
        while self.running:
            try:
                now = time.time()
                jobs_to_run = []
                
                # Find jobs that are ready to run
                for job in self.jobs.values():
                    if now >= job.next_run and not job.is_running:
                        jobs_to_run.append(job)
                
                # Execute ready jobs concurrently
                if jobs_to_run:
                    self.logger.debug(f"Executing {len(jobs_to_run)} jobs")
                    await asyncio.gather(
                        *[self._execute_job(job) for job in jobs_to_run],
                        return_exceptions=True
                    )
                
                # Wait a short time before checking again
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(1)  # Wait before retrying
    
    async def _execute_job(self, job: ScheduledJob) -> None:
        """
        Execute a single job
        :param job: The job to execute
        """
        job.is_running = True
        job.last_run = time.time()
        job.total_runs += 1
        
        try:
            self.logger.info(f"🔄 [EXECUTING] Job '{job.id}' started")
            
            # Execute the job
            result = await job.task()
            
            # Mark as successful
            job.successful_runs += 1
            job.last_error = None
            
            self.logger.info(f"✅ [COMPLETED] Job '{job.id}' completed successfully")
            
        except Exception as e:
            # Mark as failed
            job.failed_runs += 1
            job.last_error = str(e)
            
            self.logger.error(f"❌ [FAILED] Job '{job.id}' failed: {e}")
            
        finally:
            # Schedule next run (regardless of success/failure)
            job.is_running = False
            job.next_run = time.time() + job.interval
            
            self.logger.debug(f"Next run for job '{job.id}' scheduled in {job.interval}s")
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status information for a specific job
        :param job_id: Job identifier
        :return: Job status dictionary or None if not found
        """
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        now = time.time()
        
        return {
            'id': job.id,
            'interval': job.interval,
            'last_run': job.last_run,
            'next_run': job.next_run,
            'is_running': job.is_running,
            'total_runs': job.total_runs,
            'successful_runs': job.successful_runs,
            'failed_runs': job.failed_runs,
            'success_rate': (job.successful_runs / job.total_runs * 100) if job.total_runs > 0 else 0,
            'last_error': job.last_error,
            'time_until_next': max(0, job.next_run - now)
        }
    
    def get_all_jobs_status(self) -> List[Dict[str, Any]]:
        """
        Get status for all jobs
        :return: List of job status dictionaries
        """
        return [self.get_job_status(job_id) for job_id in self.jobs.keys()]
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """
        Get overall scheduler statistics
        :return: Scheduler statistics dictionary
        """
        total_jobs = len(self.jobs)
        running_jobs = sum(1 for job in self.jobs.values() if job.is_running)
        total_runs = sum(job.total_runs for job in self.jobs.values())
        total_successful = sum(job.successful_runs for job in self.jobs.values())
        total_failed = sum(job.failed_runs for job in self.jobs.values())
        
        return {
            'total_jobs': total_jobs,
            'running_jobs': running_jobs,
            'total_runs': total_runs,
            'total_successful': total_successful,
            'total_failed': total_failed,
            'overall_success_rate': (total_successful / total_runs * 100) if total_runs > 0 else 0,
            'is_running': self.running
        }