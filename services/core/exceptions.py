"""
Domain-specific exceptions with proper error context and recovery strategies.
"""

from typing import Dict, Any, Optional


class TranslationServiceError(Exception):
    """Base exception for translation service"""
    
    def __init__(self, message: str, error_code: int = 0, context: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}


class ConfigurationError(TranslationServiceError):
    """Configuration related errors"""
    pass


class APIKeyError(TranslationServiceError):
    """API key related errors"""
    pass


class APIClientError(TranslationServiceError):
    """API client related errors"""
    pass


class RateLimitError(APIClientError):
    """Rate limit related errors"""
    pass


class ValidationError(TranslationServiceError):
    """Validation related errors"""
    pass


class ServiceUnavailableError(TranslationServiceError):
    """Service unavailable errors"""
    pass


class CircuitBreakerError(TranslationServiceError):
    """Circuit breaker errors"""
    pass


class JobQueueError(TranslationServiceError):
    """Job queue related errors"""
    pass