"""
Base exception classes for the translation framework.

Following a hierarchical exception design that allows for granular error handling
while maintaining clean separation of concerns.
"""

from typing import Optional, Dict, Any
import traceback
from datetime import datetime


class TranslationFrameworkException(Exception):
    """
    Base exception for all framework-related errors.
    
    Provides consistent error handling with contextual information,
    error codes, and correlation IDs for distributed tracing.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "FRAMEWORK_ERROR",
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        inner_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.correlation_id = correlation_id
        self.inner_exception = inner_exception
        self.timestamp = datetime.utcnow()
        self.stack_trace = traceback.format_exc() if inner_exception else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging and serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace,
            "inner_exception": str(self.inner_exception) if self.inner_exception else None
        }
    
    def __str__(self) -> str:
        context_str = f" | Context: {self.context}" if self.context else ""
        correlation_str = f" | ID: {self.correlation_id}" if self.correlation_id else ""
        return f"[{self.error_code}] {self.message}{context_str}{correlation_str}"


class BusinessLogicException(TranslationFrameworkException):
    """
    Base class for business logic related exceptions.
    
    These exceptions represent violations of business rules or invalid operations
    within the domain layer.
    """
    
    def __init__(self, message: str, error_code: str = "BUSINESS_LOGIC_ERROR", **kwargs):
        super().__init__(message, error_code, **kwargs)


class InfrastructureException(TranslationFrameworkException):
    """
    Base class for infrastructure-related exceptions.
    
    These exceptions represent failures in external systems, network issues,
    or infrastructure component failures.
    """
    
    def __init__(self, message: str, error_code: str = "INFRASTRUCTURE_ERROR", **kwargs):
        super().__init__(message, error_code, **kwargs)


class ConfigurationException(TranslationFrameworkException):
    """
    Raised when there are configuration-related errors.
    
    This includes missing configuration files, invalid configuration values,
    schema validation failures, or environment setup issues.
    """
    
    def __init__(self, message: str, error_code: str = "CONFIGURATION_ERROR", **kwargs):
        super().__init__(message, error_code, **kwargs)


class ValidationException(TranslationFrameworkException):
    """
    Raised when input validation fails.
    
    This includes schema validation, business rule validation,
    or data integrity checks.
    """
    
    def __init__(
        self,
        message: str,
        validation_errors: Optional[Dict[str, str]] = None,
        error_code: str = "VALIDATION_ERROR",
        **kwargs
    ):
        super().__init__(message, error_code, **kwargs)
        self.validation_errors = validation_errors or {}
        if self.validation_errors:
            self.context["validation_errors"] = self.validation_errors