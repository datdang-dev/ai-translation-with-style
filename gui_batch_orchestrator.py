#!/usr/bin/env python3
"""
GUI-Enhanced Batch Translation Orchestrator
Extended version of batch orchestrator with GUI logging support
"""

import asyncio
import json
import time
import os
import sys
import queue
import threading
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import traceback

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from applet.batch_orchestrator import BatchTranslationOrchestrator, BatchJob
from services.common.logger import get_logger

@dataclass
class GUIJobStatus:
    """Extended job status for GUI monitoring"""
    job_id: str
    input_path: str
    output_path: str
    status: str = "pending"  # pending, processing, completed, failed, cancelled
    error: str = None
    start_time: float = None
    end_time: float = None
    progress: float = 0.0
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    log_messages: List[str] = None
    
    def __post_init__(self):
        if self.log_messages is None:
            self.log_messages = []

class GUIBatchOrchestrator(BatchTranslationOrchestrator):
    """Enhanced batch orchestrator with GUI support"""
    
    def __init__(self, config_path: str, max_concurrent: int = 3, job_delay: float = 10.0):
        super().__init__(config_path, max_concurrent, job_delay)
        
        # GUI-specific attributes
        self.gui_jobs: Dict[str, GUIJobStatus] = {}
        self.log_callbacks: Dict[str, Callable[[str], None]] = {}
        self.status_callbacks: List[Callable[[Dict[str, GUIJobStatus]], None]] = []
        self.job_counter = 0
        self.is_running = False
        self.cancel_requested = False
        
        # Thread-safe logging
        self.log_lock = threading.Lock()
        
    def add_log_callback(self, job_id: str, callback: Callable[[str], None]):
        """Add a callback for job-specific log messages"""
        self.log_callbacks[job_id] = callback
        
    def remove_log_callback(self, job_id: str):
        """Remove log callback for a job"""
        if job_id in self.log_callbacks:
            del self.log_callbacks[job_id]
            
    def add_status_callback(self, callback: Callable[[Dict[str, GUIJobStatus]], None]):
        """Add a callback for overall status updates"""
        self.status_callbacks.append(callback)
        
    def remove_status_callback(self, callback: Callable[[Dict[str, GUIJobStatus]], None]):
        """Remove status callback"""
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)
            
    def log_message(self, job_id: str, message: str, level: str = "INFO"):
        """Log a message for a specific job"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_message = f"[{timestamp}] [{level}] {message}"
        
        with self.log_lock:
            # Add to job's log messages
            if job_id in self.gui_jobs:
                self.gui_jobs[job_id].log_messages.append(formatted_message)
                
            # Call log callback if exists
            if job_id in self.log_callbacks:
                try:
                    self.log_callbacks[job_id](formatted_message)
                except Exception as e:
                    print(f"Error in log callback for {job_id}: {e}")
                    
    def update_job_status(self, job_id: str, status: str = None, progress: float = None, 
                         current_step: str = None, error: str = None):
        """Update job status and notify callbacks"""
        with self.log_lock:
            if job_id not in self.gui_jobs:
                return
                
            job = self.gui_jobs[job_id]
            
            if status is not None:
                old_status = job.status
                job.status = status
                
                # Handle status transitions
                if status == "processing" and old_status == "pending":
                    job.start_time = time.time()
                    self.log_message(job_id, f"Starting translation of {os.path.basename(job.input_path)}")
                elif status in ["completed", "failed", "cancelled"]:
                    job.end_time = time.time()
                    if job.start_time:
                        duration = job.end_time - job.start_time
                        self.log_message(job_id, f"Job {status} in {duration:.2f} seconds")
                        
            if progress is not None:
                job.progress = progress
                
            if current_step is not None:
                job.current_step = current_step
                if current_step:
                    job.completed_steps += 1
                    self.log_message(job_id, f"Step completed: {current_step}")
                    
            if error is not None:
                job.error = error
                self.log_message(job_id, f"Error: {error}", "ERROR")
                
        # Notify status callbacks
        for callback in self.status_callbacks:
            try:
                callback(self.gui_jobs.copy())
            except Exception as e:
                print(f"Error in status callback: {e}")
                
    def create_gui_job(self, input_path: str, output_path: str) -> str:
        """Create a new GUI job and return its ID"""
        self.job_counter += 1
        job_id = f"job_{self.job_counter}"
        
        gui_job = GUIJobStatus(
            job_id=job_id,
            input_path=input_path,
            output_path=output_path,
            total_steps=5  # Typical translation steps
        )
        
        self.gui_jobs[job_id] = gui_job
        self.log_message(job_id, f"Job created: {os.path.basename(input_path)} -> {os.path.basename(output_path)}")
        
        return job_id
        
    async def run_from_directory_with_gui(self, input_dir: str, output_dir: str, pattern: str = "chunk_*.json") -> Dict[str, Any]:
        """Run batch translation with GUI monitoring"""
        self.is_running = True
        self.cancel_requested = False
        
        try:
            # Find input files
            input_files = self.find_input_files(input_dir, pattern)
            if not input_files:
                return {
                    "total_jobs": 0,
                    "completed": 0,
                    "failed": 0,
                    "success_rate": 0.0,
                    "total_time": 0.0,
                    "error": f"No files found matching pattern: {pattern}"
                }
                
            # Create GUI jobs
            gui_job_ids = []
            for input_file in input_files:
                output_file = os.path.join(output_dir, os.path.basename(input_file))
                job_id = self.create_gui_job(input_file, output_file)
                gui_job_ids.append(job_id)
                
            start_time = time.time()
            
            # Create translation tasks
            tasks = []
            for i, job_id in enumerate(gui_job_ids):
                gui_job = self.gui_jobs[job_id]
                task = asyncio.create_task(
                    self.process_single_job_with_gui(gui_job, i * self.job_delay)
                )
                tasks.append(task)
                
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            
            # Calculate summary
            completed = sum(1 for result in results if result is True)
            failed = len(results) - completed
            success_rate = completed / len(results) if results else 0.0
            total_time = end_time - start_time
            
            summary = {
                "total_jobs": len(gui_job_ids),
                "completed": completed,
                "failed": failed,
                "success_rate": success_rate,
                "total_time": total_time
            }
            
            return summary
            
        except Exception as e:
            error_msg = f"Batch translation error: {str(e)}"
            for job_id in self.gui_jobs:
                if self.gui_jobs[job_id].status == "pending":
                    self.update_job_status(job_id, status="failed", error=error_msg)
                    
            return {
                "total_jobs": len(self.gui_jobs),
                "completed": 0,
                "failed": len(self.gui_jobs),
                "success_rate": 0.0,
                "total_time": 0.0,
                "error": error_msg
            }
        finally:
            self.is_running = False
            
    async def process_single_job_with_gui(self, gui_job: GUIJobStatus, delay: float = 0.0) -> bool:
        """Process a single translation job with GUI monitoring"""
        job_id = gui_job.job_id
        
        try:
            # Initial delay
            if delay > 0:
                self.log_message(job_id, f"Waiting {delay:.1f} seconds before starting...")
                await asyncio.sleep(delay)
                
            if self.cancel_requested:
                self.update_job_status(job_id, status="cancelled")
                return False
                
            # Update status to processing
            self.update_job_status(job_id, status="processing", progress=0.0)
            
            # Simulate translation steps with real orchestrator calls
            steps = [
                ("Loading configuration", 0.1),
                ("Preparing input data", 0.2),
                ("Running translation", 0.6),
                ("Post-processing", 0.85),
                ("Saving results", 1.0)
            ]
            
            for step_name, progress in steps:
                if self.cancel_requested:
                    self.update_job_status(job_id, status="cancelled")
                    return False
                    
                self.update_job_status(job_id, 
                                     progress=progress, 
                                     current_step=step_name)
                
                # Simulate processing time
                await asyncio.sleep(1.0)
                
            # Run actual translation using parent class method
            await asyncio.sleep(0.1)  # Small delay for realism
            
            # Create a batch job for the actual translation
            batch_job = BatchJob(
                input_path=gui_job.input_path,
                output_path=gui_job.output_path
            )
            
            # Process with parent orchestrator
            success = await self.process_single_file(batch_job)
            
            if success:
                self.update_job_status(job_id, status="completed", progress=1.0)
                self.log_message(job_id, "Translation completed successfully!")
                return True
            else:
                error_msg = batch_job.error or "Translation failed"
                self.update_job_status(job_id, status="failed", error=error_msg)
                self.log_message(job_id, f"Translation failed: {error_msg}", "ERROR")
                return False
                
        except Exception as e:
            error_msg = f"Job processing error: {str(e)}"
            self.update_job_status(job_id, status="failed", error=error_msg)
            self.log_message(job_id, f"Exception occurred: {traceback.format_exc()}", "ERROR")
            return False
            
    def find_input_files(self, input_dir: str, pattern: str) -> List[str]:
        """Find input files matching the pattern"""
        import glob
        search_pattern = os.path.join(input_dir, pattern)
        files = glob.glob(search_pattern)
        return sorted(files)
        
    def cancel_all_jobs(self):
        """Cancel all pending and running jobs"""
        self.cancel_requested = True
        
        for job_id, job in self.gui_jobs.items():
            if job.status in ["pending", "processing"]:
                self.update_job_status(job_id, status="cancelled")
                self.log_message(job_id, "Job cancelled by user request")
                
    def get_job_summary(self) -> Dict[str, int]:
        """Get summary of job statuses"""
        summary = {
            "total": len(self.gui_jobs),
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0
        }
        
        for job in self.gui_jobs.values():
            summary[job.status] += 1
            
        return summary
        
    def get_job_by_id(self, job_id: str) -> Optional[GUIJobStatus]:
        """Get job by ID"""
        return self.gui_jobs.get(job_id)
        
    def clear_completed_jobs(self):
        """Clear completed, failed, and cancelled jobs"""
        to_remove = []
        for job_id, job in self.gui_jobs.items():
            if job.status in ["completed", "failed", "cancelled"]:
                to_remove.append(job_id)
                
        for job_id in to_remove:
            del self.gui_jobs[job_id]
            if job_id in self.log_callbacks:
                del self.log_callbacks[job_id]
                
    def export_job_logs(self, job_id: str, filename: str):
        """Export job logs to file"""
        if job_id not in self.gui_jobs:
            return False
            
        try:
            job = self.gui_jobs[job_id]
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Job Log for {job_id}\n")
                f.write(f"{'='*50}\n")
                f.write(f"Input: {job.input_path}\n")
                f.write(f"Output: {job.output_path}\n")
                f.write(f"Status: {job.status}\n")
                f.write(f"Progress: {job.progress:.1%}\n")
                if job.start_time:
                    f.write(f"Start Time: {datetime.fromtimestamp(job.start_time)}\n")
                if job.end_time:
                    f.write(f"End Time: {datetime.fromtimestamp(job.end_time)}\n")
                    f.write(f"Duration: {job.end_time - job.start_time:.2f} seconds\n")
                if job.error:
                    f.write(f"Error: {job.error}\n")
                f.write(f"\nLog Messages:\n")
                f.write(f"{'-'*30}\n")
                for message in job.log_messages:
                    f.write(f"{message}\n")
                    
            return True
        except Exception as e:
            print(f"Error exporting logs: {e}")
            return False


# Convenience function for GUI integration
def create_gui_orchestrator(config_path: str, max_concurrent: int = 3, job_delay: float = 10.0) -> GUIBatchOrchestrator:
    """Create a GUI-enabled batch orchestrator"""
    return GUIBatchOrchestrator(config_path, max_concurrent, job_delay)