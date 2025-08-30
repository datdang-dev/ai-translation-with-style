"""
Core Manager
Single entry point for all middleware operations
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from services.infrastructure import ConfigManager, APIKeyManager, JobScheduler
from services.translation import RequestManager, Validator, Standardizer
from services.common.logger import get_logger
from services.common.error_codes import ERR_NONE

@dataclass
class TranslationJob:
    """Represents a translation job"""
    id: str
    input_path: str
    output_path: str
    status: str = "pending"  # pending, processing, completed, failed
    error: str = None
    start_time: float = None
    end_time: float = None
    result: Dict[str, Any] = None

class CoreManager:
    """Single entry point for all middleware operations"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize core manager
        :param config_path: Path to configuration file
        """
        self.logger = get_logger("CoreManager")
        
        # Initialize infrastructure services
        self.config_manager = ConfigManager(config_path)
        self.key_manager = None
        self.job_scheduler = None
        
        # Initialize translation services
        self.request_manager = None
        self.validator = None
        self.standardizer = None
        
        # Initialize components
        self._initialize_components()
        
        self.logger.info("CoreManager initialized successfully")
    
    def _initialize_components(self) -> None:
        """Initialize all middleware components"""
        try:
            # Load API keys
            api_keys = self._load_api_keys()
            
            # Initialize key manager
            api_config = self.config_manager.get_api_config()
            self.key_manager = APIKeyManager(
                api_keys=api_keys,
                max_retries=api_config.get("max_retries", 3),
                backoff_base=api_config.get("backoff_base", 2.0),
                max_requests_per_minute=api_config.get("max_requests_per_minute", 20)
            )
            
            # Initialize job scheduler
            scheduling_config = self.config_manager.get_scheduling_config()
            self.job_scheduler = JobScheduler(
                default_interval=scheduling_config.get("job_delay", 10.0)
            )
            
            # Initialize request manager
            self.request_manager = RequestManager(
                key_manager=self.key_manager,
                api_url=api_config.get("url"),
                config=api_config
            )
            
            # Initialize validator
            validation_config = self.config_manager.get_validation_config()
            self.validator = Validator()
            
            # Initialize standardizer
            standardization_config = self.config_manager.get_standardization_config()
            self.standardizer = Standardizer(
                auto_convert=standardization_config.get("auto_convert", True)
            )
            
            self.logger.info("All middleware components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise
    
    def _load_api_keys(self) -> List[str]:
        """Load API keys from configuration"""
        try:
            # Try to load from api_keys.json first
            api_keys_path = "config/api_keys.json"
            if Path(api_keys_path).exists():
                with open(api_keys_path, 'r', encoding='utf-8') as f:
                    api_keys_config = json.load(f)
                    api_keys = api_keys_config.get("api_keys", [])
                    if api_keys:
                        self.logger.info(f"Loaded {len(api_keys)} API keys from {api_keys_path}")
                        return api_keys
            
            # Fallback to empty list
            self.logger.warning("No API keys found, please configure in config/api_keys.json")
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to load API keys: {e}")
            return []
    
    async def start_scheduler(self) -> None:
        """Start the job scheduler"""
        if self.job_scheduler:
            await self.job_scheduler.start()
            self.logger.info("Job scheduler started")
    
    async def stop_scheduler(self) -> None:
        """Stop the job scheduler"""
        if self.job_scheduler:
            await self.job_scheduler.stop()
            self.logger.info("Job scheduler stopped")
    
    def add_translation_job(self, job_id: str, input_path: str, output_path: str, 
                           interval: float = None) -> None:
        """
        Add a translation job to the scheduler
        :param job_id: Unique job identifier
        :param input_path: Path to input file
        :param output_path: Path to output file
        :param interval: Job execution interval (uses default if None)
        """
        if not self.job_scheduler:
            raise RuntimeError("Job scheduler not initialized")
        
        # Create job task
        async def translation_task():
            return await self._execute_translation_job(input_path, output_path)
        
        # Add to scheduler
        self.job_scheduler.add_job(job_id, translation_task, interval)
        self.logger.info(f"Added translation job '{job_id}' for {input_path}")
    
    async def _execute_translation_job(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """
        Execute a single translation job
        :param input_path: Input file path
        :param output_path: Output file path
        :return: Job result
        """
        try:
            self.logger.info(f"🔄 [EXECUTING] Translation job: {input_path} -> {output_path}")
            
            # Standardize input
            standardized_input = self.standardizer.standardize(input_path)
            
            # Prepare translation request
            request_data = self._prepare_translation_request(standardized_input)
            
            # Send request
            error_code, response = await self.request_manager.send_request(request_data)
            
            if error_code != ERR_NONE:
                raise RuntimeError(f"Translation request failed with error code: {error_code}")
            
            # Validate response
            validated_response = self.validator.validate_and_raise(response)
            
            # Save result
            self._save_translation_result(output_path, validated_response)
            
            self.logger.info(f"✅ [COMPLETED] Translation job: {input_path}")
            return {"status": "success", "input_path": input_path, "output_path": output_path}
            
        except Exception as e:
            error_msg = f"Translation job failed: {str(e)}"
            self.logger.error(f"❌ [FAILED] {error_msg}")
            return {"status": "failed", "input_path": input_path, "error": error_msg}
    
    def _prepare_translation_request(self, text_dict: Dict[str, str]) -> Dict[str, Any]:
        """
        Prepare translation request data
        :param text_dict: Standardized text dictionary
        :return: Request data for API
        """
        # Get translation configuration
        translation_config = self.config_manager.get_translation_config()
        
        # Get prompts
        system_message = self.config_manager.get_prompt("system_message", "")
        format_rules = self.config_manager.get_prompt("format_rules", "")
        style_rules = self.config_manager.get_prompt("style_rules", "")
        translation_flow = self.config_manager.get_prompt("translation_flow", "")
        
        # Prepare messages
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        # Add format and style rules
        if format_rules:
            messages.append({"role": "user", "content": format_rules})
        if style_rules:
            messages.append({"role": "user", "content": style_rules})
        if translation_flow:
            messages.append({"role": "system", "content": translation_flow})
        
        # Add the text to translate
        json_text = json.dumps(text_dict, ensure_ascii=False, indent=2)
        messages.append({"role": "user", "content": json_text})
        
        # Build request data
        request_data = {
            "model": translation_config.get("model", "google/gemini-2.0-flash-exp:free"),
            "messages": messages,
            "temperature": translation_config.get("temperature", 1),
            "presence_penalty": translation_config.get("presence_penalty", 0.0),
            "frequency_penalty": translation_config.get("frequency_penalty", 0.0),
            "top_p": translation_config.get("top_p", 1),
            "top_k": translation_config.get("top_k", 50),
            "min_p": translation_config.get("min_p", 0),
            "top_a": translation_config.get("top_a", 1),
            "repetition_penalty": translation_config.get("repetition_penalty", 1.2)
        }
        
        return request_data
    
    def _save_translation_result(self, output_path: str, result: Dict[str, Any]) -> None:
        """
        Save translation result to file
        :param output_path: Output file path
        :param result: Translation result
        """
        try:
            # Ensure output directory exists
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save result
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Translation result saved to: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save translation result: {e}")
            raise
    
    async def process_batch_translation(self, input_dir: str, output_dir: str, 
                                      pattern: str = "*.json") -> Dict[str, Any]:
        """
        Process batch translation from directory
        :param input_dir: Input directory path
        :param output_dir: Output directory path
        :param input_pattern: File pattern to match
        :return: Batch processing summary
        """
        try:
            start_time = time.time()
            
            # Find input files
            input_path = Path(input_dir)
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Find matching files and sort numerically
            file_paths = list(input_path.glob(pattern))
            file_paths.sort(key=lambda x: self._extract_file_number(x.name))
            
            if not file_paths:
                return {
                    "total_jobs": 0,
                    "completed": 0,
                    "failed": 0,
                    "total_time": 0,
                    "success_rate": 0.0
                }
            
            # Add jobs to scheduler
            for i, file_path in enumerate(file_paths):
                if file_path.is_file():
                    output_file = output_path / file_path.name
                    job_id = f"translation_{i+1}_{file_path.stem}"
                    
                    self.add_translation_job(job_id, str(file_path), str(output_file))
            
            # Start scheduler
            await self.start_scheduler()
            
            # Wait for all jobs to complete
            while True:
                stats = self.job_scheduler.get_scheduler_stats()
                if stats["total_runs"] >= len(file_paths):
                    break
                await asyncio.sleep(1)
            
            # Stop scheduler
            await self.stop_scheduler()
            
            # Calculate summary
            total_time = time.time() - start_time
            scheduler_stats = self.job_scheduler.get_scheduler_stats()
            
            summary = {
                "total_jobs": len(file_paths),
                "completed": scheduler_stats["total_successful"],
                "failed": scheduler_stats["total_failed"],
                "total_time": total_time,
                "success_rate": scheduler_stats["overall_success_rate"] / 100
            }
            
            self.logger.info(f"Batch translation completed: {summary}")
            return summary
            
        except Exception as e:
            self.logger.error(f"Batch translation failed: {e}")
            raise
    
    def _extract_file_number(self, filename: str) -> int:
        """Extract number from filename for sorting"""
        import re
        match = re.search(r'(\d+)', filename)
        return int(match.group(1)) if match else 0
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get overall system status
        :return: System status dictionary
        """
        return {
            "config": {
                "api": self.config_manager.get_api_config(),
                "scheduling": self.config_manager.get_scheduling_config(),
                "validation": self.config_manager.get_validation_config(),
                "standardization": self.config_manager.get_standardization_config()
            },
            "key_manager": self.key_manager.get_key_stats() if self.key_manager else None,
            "scheduler": self.job_scheduler.get_scheduler_stats() if self.job_scheduler else None,
            "request_manager": self.request_manager.get_request_stats() if self.request_manager else None,
            "validator": self.validator.get_validation_stats() if self.validator else None,
            "standardizer": self.standardizer.get_standardization_stats() if self.standardizer else None
        }