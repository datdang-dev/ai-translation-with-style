"""
Translation Orchestrator Service
Backward compatibility layer for the new architecture
"""

# Import from the new architecture
from applet.translation_orchestrator import (
    TranslationOrchestrator,
    run_batch_translation_from_directory
)

# Import legacy functions for backward compatibility
from services.translation_service.translation_service import (
    run_translation,
    run_batch_translation
)

# Export all functions for backward compatibility
__all__ = [
    "TranslationOrchestrator",
    "run_translation", 
    "run_batch_translation",
    "run_batch_translation_from_directory"
]