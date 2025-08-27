"""
Translation Orchestrator - Main applet for translation operations
New architecture implementation replacing the old service
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from services.config import ServiceFactory, ConfigurationManager
from services.models import (
    TranslationRequest, TranslationResult, BatchResult, 
    FormatType, ProviderType
)
from services.middleware import TranslationManager
from services.common.logger import get_logger


class TranslationOrchestrator:
    """Main translation orchestrator applet for the new architecture"""
    
    def __init__(self, config_path: str = None):
        """
        Initialize Translation Orchestrator
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.logger = get_logger("TranslationOrchestrator")
        
        # Initialize configuration and services
        config_manager = ConfigurationManager(config_path) if config_path else ConfigurationManager()
        self.service_factory = ServiceFactory(config_manager)
        
        # Core services
        self.translation_manager: Optional[TranslationManager] = None
        self._initialized = False
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize all services"""
        if self._initialized:
            return {"status": "already_initialized"}
        
        self.logger.info("Initializing Translation Orchestrator...")
        
        try:
            # Initialize all services
            init_result = await self.service_factory.initialize_all_services()
            
            if not init_result['success']:
                raise Exception(f"Service initialization failed: {init_result.get('error')}")
            
            # Get main translation manager
            self.translation_manager = self.service_factory.get_translation_manager()
            
            # Start health monitoring
            await self.service_factory.start_health_monitoring()
            
            self._initialized = True
            self.logger.info("Translation Orchestrator initialized successfully")
            
            return {
                "status": "success",
                "services_initialized": init_result['services_created'],
                "providers_available": init_result['providers_available'],
                "cache_enabled": init_result['cache_enabled']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Translation Orchestrator: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _ensure_initialized(self):
        """Ensure orchestrator is initialized"""
        if not self._initialized:
            raise RuntimeError("Translation Orchestrator not initialized. Call initialize() first.")
    
    async def translate_renpy(self, 
                            requests: Union[List[str], List[TranslationRequest]], 
                            target_lang: str,
                            source_lang: str = "auto") -> Dict[str, Any]:
        """
        Translate Renpy content
        
        Args:
            requests: List of Renpy content strings or TranslationRequest objects
            target_lang: Target language code
            source_lang: Source language code (default: auto-detect)
            
        Returns:
            Dictionary with translation results and statistics
        """
        self._ensure_initialized()
        
        self.logger.info(f"Starting Renpy translation: {len(requests)} items to {target_lang}")
        
        # Convert strings to TranslationRequest objects if needed
        if requests and isinstance(requests[0], str):
            translation_requests = []
            for i, content in enumerate(requests):
                request = TranslationRequest(
                    content=content,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    format_type=FormatType.RENPY,
                    request_id=f"renpy_{i}_{int(time.time())}"
                )
                translation_requests.append(request)
        else:
            translation_requests = requests
        
        # Process batch
        batch_result = await self.translation_manager.translate_renpy_batch(
            [req.content for req in translation_requests],
            target_lang,
            source_lang
        )
        
        # Format response
        return self._format_batch_response(batch_result, "renpy")
    
    async def translate_json(self, 
                           requests: Union[List[Any], List[TranslationRequest]], 
                           target_lang: str,
                           source_lang: str = "auto") -> Dict[str, Any]:
        """
        Translate JSON content
        
        Args:
            requests: List of JSON data or TranslationRequest objects
            target_lang: Target language code
            source_lang: Source language code (default: auto-detect)
            
        Returns:
            Dictionary with translation results and statistics
        """
        self._ensure_initialized()
        
        self.logger.info(f"Starting JSON translation: {len(requests)} items to {target_lang}")
        
        # Convert data to TranslationRequest objects if needed
        if requests and not isinstance(requests[0], TranslationRequest):
            translation_requests = []
            for i, content in enumerate(requests):
                request = TranslationRequest(
                    content=content,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    format_type=FormatType.JSON,
                    request_id=f"json_{i}_{int(time.time())}"
                )
                translation_requests.append(request)
        else:
            translation_requests = requests
        
        # Process batch
        batch_result = await self.translation_manager.translate_json_batch(
            [req.content for req in translation_requests],
            target_lang,
            source_lang
        )
        
        # Format response
        return self._format_batch_response(batch_result, "json")
    
    async def translate_text(self, 
                           requests: Union[List[str], List[TranslationRequest]], 
                           target_lang: str,
                           source_lang: str = "auto") -> Dict[str, Any]:
        """
        Translate plain text content
        
        Args:
            requests: List of text strings or TranslationRequest objects
            target_lang: Target language code
            source_lang: Source language code (default: auto-detect)
            
        Returns:
            Dictionary with translation results and statistics
        """
        self._ensure_initialized()
        
        self.logger.info(f"Starting TEXT translation: {len(requests)} items to {target_lang}")
        
        # Convert data to TranslationRequest objects if needed
        if requests and not isinstance(requests[0], TranslationRequest):
            translation_requests = []
            for i, content in enumerate(requests):
                request = TranslationRequest(
                    content=content,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    format_type=FormatType.TEXT,
                    request_id=f"text_{i}_{int(time.time())}"
                )
                translation_requests.append(request)
        else:
            translation_requests = requests
        
        # Process batch
        batch_result = await self.translation_manager.translate_text_batch(
            [req.content for req in translation_requests],
            target_lang,
            source_lang
        )
        
        # Format response
        return self._format_batch_response(batch_result, "text")
    
    async def translate_directory(self, 
                                input_dir: str,
                                output_dir: str,
                                target_lang: str,
                                pattern: str = "*.json",
                                source_lang: str = "auto",
                                format_type: str = "json") -> Dict[str, Any]:
        """
        Translate all files in a directory
        
        Args:
            input_dir: Input directory path
            output_dir: Output directory path
            target_lang: Target language code
            pattern: File pattern to match (default: *.json)
            source_lang: Source language code (default: auto-detect)
            format_type: Content format type (default: json)
            
        Returns:
            Dictionary with translation results and statistics
        """
        self._ensure_initialized()
        
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        
        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Find matching files
        files = list(input_path.glob(pattern))
        if not files:
            self.logger.warning(f"No files found matching pattern {pattern} in {input_dir}")
            return {
                "status": "no_files",
                "message": f"No files found matching pattern {pattern}",
                "input_dir": input_dir,
                "pattern": pattern
            }
        
        # Sort files for consistent processing order
        files.sort()
        
        self.logger.info(f"Found {len(files)} files matching pattern {pattern}")
        
        # Process files
        translation_requests = []
        file_mappings = []
        
        for file_path in files:
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    if format_type.lower() == "json":
                        import json
                        content = json.load(f)
                    else:
                        content = f.read()
                
                # Create translation request
                request = TranslationRequest(
                    content=content,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    format_type=FormatType.JSON if format_type.lower() == "json" else FormatType.RENPY,
                    request_id=f"file_{file_path.stem}_{int(time.time())}"
                )
                
                translation_requests.append(request)
                
                # Map to output file
                output_file = output_path / file_path.name
                file_mappings.append({
                    "input_file": str(file_path),
                    "output_file": str(output_file),
                    "request_id": request.request_id
                })
                
            except Exception as e:
                self.logger.error(f"Failed to read file {file_path}: {e}")
                continue
        
        if not translation_requests:
            return {
                "status": "error",
                "message": "No files could be processed",
                "files_found": len(files)
            }
        
        # Process batch translation
        start_time = time.time()
        
        if format_type.lower() == "json":
            batch_result = await self.translation_manager.translate_json_batch(
                [req.content for req in translation_requests],
                target_lang,
                source_lang
            )
        else:
            batch_result = await self.translation_manager.translate_renpy_batch(
                [req.content for req in translation_requests],
                target_lang,
                source_lang
            )
        
        # Save results to files
        saved_files = []
        failed_files = []
        
        for i, (result, mapping) in enumerate(zip(batch_result.results, file_mappings)):
            try:
                output_file = Path(mapping["output_file"])
                
                if result.validation_passed and result.translated is not None:
                    # Save translated content
                    with open(output_file, 'w', encoding='utf-8') as f:
                        if format_type.lower() == "json":
                            import json
                            json.dump(result.translated, f, indent=2, ensure_ascii=False)
                        else:
                            f.write(str(result.translated))
                    
                    saved_files.append(str(output_file))
                    self.logger.debug(f"Saved translated file: {output_file}")
                else:
                    failed_files.append({
                        "file": mapping["input_file"],
                        "error": result.validation_details.get('error', 'Translation failed')
                    })
                    
            except Exception as e:
                self.logger.error(f"Failed to save file {mapping['output_file']}: {e}")
                failed_files.append({
                    "file": mapping["input_file"],
                    "error": f"Save error: {e}"
                })
        
        total_time = time.time() - start_time
        
        # Format response
        return {
            "status": "completed",
            "input_dir": input_dir,
            "output_dir": output_dir,
            "pattern": pattern,
            "format_type": format_type,
            "target_language": target_lang,
            "source_language": source_lang,
            "files_found": len(files),
            "files_processed": len(translation_requests),
            "files_saved": len(saved_files),
            "files_failed": len(failed_files),
            "success_rate": (len(saved_files) / len(translation_requests)) * 100 if translation_requests else 0,
            "total_time": total_time,
            "average_time_per_file": total_time / len(translation_requests) if translation_requests else 0,
            "cache_hit_rate": batch_result.cache_hit_rate,
            "saved_files": saved_files,
            "failed_files": failed_files,
            "batch_details": {
                "batch_id": batch_result.batch_id,
                "total_requests": batch_result.total_requests,
                "successful_translations": batch_result.successful_translations,
                "failed_translations": batch_result.failed_translations
            }
        }
    
    def _format_batch_response(self, batch_result: BatchResult, operation_type: str) -> Dict[str, Any]:
        """Format batch result into response dictionary"""
        return {
            "status": "completed",
            "operation_type": operation_type,
            "batch_id": batch_result.batch_id,
            "total_requests": batch_result.total_requests,
            "successful_translations": batch_result.successful_translations,
            "failed_translations": batch_result.failed_translations,
            "success_rate": batch_result.success_rate,
            "total_time": batch_result.total_processing_time,
            "average_time": batch_result.average_processing_time,
            "cache_hit_rate": batch_result.cache_hit_rate,
            "started_at": batch_result.started_at.isoformat(),
            "completed_at": batch_result.completed_at.isoformat() if batch_result.completed_at else None,
            "results": [
                {
                    "request_id": result.request_id,
                    "original": result.original,
                    "translated": result.translated,
                    "provider": result.provider,
                    "from_cache": result.from_cache,
                    "processing_time": result.processing_time,
                    "validation_passed": result.validation_passed
                }
                for result in batch_result.results
            ],
            "errors": batch_result.errors
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        if not self._initialized:
            return {
                "initialized": False,
                "status": "not_initialized"
            }
        
        service_status = self.service_factory.get_service_status()
        translation_status = self.translation_manager.get_status()
        
        return {
            "initialized": True,
            "status": "ready",
            "service_factory": service_status,
            "translation_manager": translation_status
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get orchestrator capabilities"""
        if not self._initialized:
            return {"error": "Not initialized"}
        
        service_status = self.service_factory.get_service_status()
        
        capabilities = {
            "formats_supported": ["renpy", "json", "text"],
            "providers_available": service_status.get('providers', {}).get('providers', []),
            "cache_enabled": 'cache_service' in service_status.get('services_created', []),
            "validation_enabled": True,
            "health_monitoring": True,
            "resiliency_features": [
                "retry_with_backoff",
                "circuit_breaker", 
                "provider_fallback",
                "graceful_degradation"
            ],
            "batch_processing": True,
            "directory_processing": True
        }
        
        return capabilities
    
    async def shutdown(self):
        """Gracefully shutdown orchestrator"""
        self.logger.info("Shutting down Translation Orchestrator...")
        
        try:
            if self.translation_manager:
                await self.translation_manager.shutdown()
            
            await self.service_factory.stop_health_monitoring()
            
            self._initialized = False
            self.logger.info("Translation Orchestrator shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    @classmethod
    def from_config(cls, config_path: str) -> 'TranslationOrchestrator':
        """Create orchestrator from configuration file"""
        return cls(config_path)
    
    @classmethod 
    def create_default(cls) -> 'TranslationOrchestrator':
        """Create orchestrator with default configuration"""
        return cls()


# Backward compatibility functions for existing demos
async def run_batch_translation_from_directory(
    config_path: str,
    input_dir: str,
    output_dir: str,
    pattern: str = "*.json",
    max_concurrent: int = 3,
    job_delay: float = 10.0,
    target_lang: str = "vi",
    source_lang: str = "auto"
) -> Dict[str, Any]:
    """
    Backward compatibility function for existing batch translation demos
    """
    orchestrator = TranslationOrchestrator.from_config(config_path)
    
    try:
        # Initialize orchestrator
        init_result = await orchestrator.initialize()
        if init_result["status"] != "success":
            raise Exception(f"Failed to initialize: {init_result}")
        
        # Update configuration for compatibility
        orchestrator.translation_manager.update_configuration(
            max_concurrent=max_concurrent,
            job_delay=job_delay
        )
        
        # Determine format from pattern
        format_type = "json" if pattern.endswith(".json") else "renpy"
        
        # Run directory translation
        result = await orchestrator.translate_directory(
            input_dir=input_dir,
            output_dir=output_dir,
            target_lang=target_lang,
            pattern=pattern,
            source_lang=source_lang,
            format_type=format_type
        )
        
        # Convert to old format for compatibility
        return {
            "completed": result.get("files_saved", 0),
            "failed": result.get("files_failed", 0),
            "total_jobs": result.get("files_processed", 0),
            "total_time": result.get("total_time", 0),
            "success_rate": result.get("success_rate", 0) / 100,  # Convert back to 0-1 range
            "cache_hit_rate": result.get("cache_hit_rate", 0),
            "details": result
        }
        
    finally:
        await orchestrator.shutdown()


# Export main classes and functions
__all__ = [
    'TranslationOrchestrator',
    'run_batch_translation_from_directory'
]
