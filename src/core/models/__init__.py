"""Core domain models for the translation framework"""

from .translation_request import TranslationRequest
from .translation_result import TranslationResult, TranslationError
from .provider_config import ProviderConfig, ProviderType

__all__ = [
    "TranslationRequest",
    "TranslationResult", 
    "TranslationError",
    "ProviderConfig",
    "ProviderType",
]