"""
Exception hierarchy for the translation framework.
"""

from .base_exceptions import (
    TranslationFrameworkException,
    BusinessLogicException,
    InfrastructureException,
    ConfigurationException,
    ValidationException
)

from .translation_exceptions import (
    TranslationException,
    ProviderException,
    QualityAssuranceException,
    ContentProcessingException
)

from .provider_exceptions import (
    ProviderConnectionException,
    ProviderAuthenticationException,
    ProviderRateLimitException,
    ProviderTimeoutException
)

__all__ = [
    "TranslationFrameworkException",
    "BusinessLogicException", 
    "InfrastructureException",
    "ConfigurationException",
    "ValidationException",
    "TranslationException",
    "ProviderException",
    "QualityAssuranceException", 
    "ContentProcessingException",
    "ProviderConnectionException",
    "ProviderAuthenticationException",
    "ProviderRateLimitException",
    "ProviderTimeoutException"
]