"""
Translation Applet
Single component handling all translation logic including batch processing
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass

from middleware import CoreManager
from services.common.logger import get_logger

@dataclass
class TranslationResult:
    """Represents a translation result"""
    input_path: str
    output_path: str
    status: str
    error: Optional[str] = None
    processing_time: float = 0.0
    word_count: int = 0

class TranslationApplet:
    """Single translation component using the new middleware architecture"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize translation applet
        :param config_path: Path to configuration file
        """
        self.logger = get_logger("TranslationApplet")
        self.core_manager = CoreManager(config_path)
        self.logger.info("TranslationApplet initialized successfully")
    
    async def translate_single_file(self, input_path: str, output_path: str) -> TranslationResult:
        """
        Translate a single file
        :param input_path: Path to input file
        :param output_path: Path to output file
        :return: Translation result
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting single file translation: {input_path}")
            
            # Add single job to scheduler
            job_id = f"single_{Path(input_path).stem}"
            self.core_manager.add_translation_job(job_id, input_path, output_path)
            
            # Start scheduler
            await self.core_manager.start_scheduler()
            
            # Wait for job to complete
            while True:
                job_status = self.core_manager.job_scheduler.get_job_status(job_id)
                if job_status and job_status["total_runs"] > 0:
                    break
                await asyncio.sleep(0.1)
            
            # Stop scheduler
            await self.core_manager.stop_scheduler()
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Check if output file was created
            if Path(output_path).exists():
                # Count words in output
                word_count = self._count_words_in_file(output_path)
                
                result = TranslationResult(
                    input_path=input_path,
                    output_path=output_path,
                    status="completed",
                    processing_time=processing_time,
                    word_count=word_count
                )
                
                self.logger.info(f"Single file translation completed: {input_path}")
                return result
            else:
                result = TranslationResult(
                    input_path=input_path,
                    output_path=output_path,
                    status="failed",
                    error="Output file not created",
                    processing_time=processing_time
                )
                
                self.logger.error(f"Single file translation failed: {input_path}")
                return result
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Translation failed: {str(e)}"
            
            result = TranslationResult(
                input_path=input_path,
                output_path=output_path,
                status="failed",
                error=error_msg,
                processing_time=processing_time
            )
            
            self.logger.error(f"Single file translation failed: {input_path} - {error_msg}")
            return result
    
    async def translate_batch_from_directory(self, input_dir: str, output_dir: str, 
                                          pattern: str = "chunk_*.json") -> Dict[str, Any]:
        """
        Translate multiple files from directory using batch processing
        :param input_dir: Input directory path
        :param output_dir: Output directory path
        :param pattern: File pattern to match
        :return: Batch processing summary
        """
        try:
            self.logger.info(f"Starting batch translation from: {input_dir}")
            
            # Use core manager for batch processing
            summary = await self.core_manager.process_batch_translation(
                input_dir=input_dir,
                output_dir=output_dir,
                pattern=pattern
            )
            
            self.logger.info(f"Batch translation completed: {summary}")
            return summary
            
        except Exception as e:
            error_msg = f"Batch translation failed: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "total_jobs": 0,
                "completed": 0,
                "failed": 1,
                "total_time": 0,
                "success_rate": 0.0,
                "error": error_msg
            }
    
    async def translate_text(self, text_dict: Dict[str, str]) -> Dict[str, str]:
        """
        Translate text dictionary directly
        :param text_dict: Dictionary with text to translate
        :return: Translated text dictionary
        """
        try:
            self.logger.info("Starting direct text translation")
            
            # Standardize input
            standardized_input = self.core_manager.standardizer.standardize(text_dict)
            
            # Prepare translation request
            request_data = self.core_manager._prepare_translation_request(standardized_input)
            
            # Send request
            error_code, response = await self.core_manager.request_manager.send_request(request_data)
            
            if error_code != 0:  # ERR_NONE
                raise RuntimeError(f"Translation request failed with error code: {error_code}")
            
            # Validate response
            validated_response = self.core_manager.validator.validate_and_raise(response)
            
            self.logger.info("Direct text translation completed")
            return validated_response
            
        except Exception as e:
            error_msg = f"Direct text translation failed: {str(e)}"
            self.logger.error(error_msg)
            raise
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status information
        :return: System status dictionary
        """
        return self.core_manager.get_system_status()
    
    def _count_words_in_file(self, file_path: str) -> int:
        """
        Count words in a file
        :param file_path: Path to file
        :return: Word count
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Simple word counting (split by whitespace)
                words = content.split()
                return len(words)
        except Exception:
            return 0
    
    async def health_check(self) -> bool:
        """
        Perform health check on the translation system
        :return: True if healthy, False otherwise
        """
        try:
            # Check if core manager is properly initialized
            if not self.core_manager:
                return False
            
            # Check if all components are available
            if not all([
                self.core_manager.config_manager,
                self.core_manager.key_manager,
                self.core_manager.job_scheduler,
                self.core_manager.request_manager,
                self.core_manager.validator,
                self.core_manager.standardizer
            ]):
                return False
            
            # Perform API health check
            api_healthy = await self.core_manager.request_manager.health_check()
            
            return api_healthy
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported input formats
        :return: List of format names
        """
        if self.core_manager.standardizer:
            return self.core_manager.standardizer.get_supported_formats()
        return []
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get configuration summary
        :return: Configuration summary dictionary
        """
        if self.core_manager.config_manager:
            return {
                "api_config": self.core_manager.config_manager.get_api_config(),
                "translation_config": self.core_manager.config_manager.get_translation_config(),
                "scheduling_config": self.core_manager.config_manager.get_scheduling_config(),
                "validation_config": self.core_manager.config_manager.get_validation_config(),
                "standardization_config": self.core_manager.config_manager.get_standardization_config()
            }
        return {}