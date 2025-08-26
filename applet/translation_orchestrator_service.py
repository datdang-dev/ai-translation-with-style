"""
Translation Orchestrator Service
New architecture interface
"""

# Import from the new architecture
from applet.translation_orchestrator import (
    TranslationOrchestrator,
    run_batch_translation_from_directory
)

# Export all functions
__all__ = [
    "TranslationOrchestrator",
    "run_batch_translation_from_directory"
]