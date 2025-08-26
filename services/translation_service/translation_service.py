"""
Main translation service module
Exposes the public API for translation functionality
"""

from typing import List, Dict, Any, Optional
from services.translation_service.translation_core import TranslationCore
from services.translation_service.batch_processor import BatchProcessor
from services.translation_service.models import BatchJob


async def run_translation(config_path: str, input_path: str, output_path: str) -> bool:
    """
    Utility function to run translation process
    :param config_path: Configuration file path
    :param input_path: Input file path
    :param output_path: Output file path
    :return: True if successful, False if failed
    """
    translator = TranslationCore(config_path)
    return await translator.translate_file(input_path, output_path)


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
    :param job_delay: Delay in seconds between jobs to avoid rate limiting
    :return: Processing summary
    """
    if len(input_files) != len(output_files):
        raise ValueError("Input and output file lists must have the same length")
    
    processor = BatchProcessor(config_path, max_concurrent, job_delay)
    
    # Add jobs
    for input_file, output_file in zip(input_files, output_files):
        processor.add_job(input_file, output_file)
    
    # Process all jobs
    return await processor.process_all_jobs()


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
    :param job_delay: Delay in seconds between jobs to avoid rate limiting
    :return: Processing summary
    """
    processor = BatchProcessor(config_path, max_concurrent, job_delay)
    
    # Add jobs from directory
    processor.add_jobs_from_directory(input_dir, output_dir, pattern)
    
    # Process all jobs
    return await processor.process_all_jobs()