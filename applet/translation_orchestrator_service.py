"""
Translation Orchestrator Service
Direct interface to the new service-based implementation
"""

from services.translation_service.translation_service import (
    run_translation,
    run_batch_translation,
    run_batch_translation_from_directory
)

# Export the functions directly
__all__ = [
    "run_translation",
    "run_batch_translation",
    "run_batch_translation_from_directory"
]