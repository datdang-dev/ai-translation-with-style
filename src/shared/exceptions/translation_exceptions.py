"""
Translation-specific exception classes.

These exceptions handle errors related to translation processes,
quality assurance, and content processing.
"""

from typing import Optional, Dict, Any, List
from .base_exceptions import BusinessLogicException, InfrastructureException


class TranslationException(BusinessLogicException):
    """
    Base exception for translation-related errors.
    
    Covers errors during the translation process including content validation,
    prompt generation, and response processing.
    """
    
    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        error_code: str = "TRANSLATION_ERROR",
        **kwargs
    ):
        context = kwargs.get("context", {})
        if job_id:
            context["job_id"] = job_id
        if provider:
            context["provider"] = provider
        if model:
            context["model"] = model
        kwargs["context"] = context
        
        super().__init__(message, error_code, **kwargs)
        self.job_id = job_id
        self.provider = provider
        self.model = model


class ProviderException(InfrastructureException):
    """
    Exception for provider-related errors.
    
    Handles errors specific to translation provider interactions,
    including API failures, authentication issues, and service unavailability.
    """
    
    def __init__(
        self,
        message: str,
        provider: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        error_code: str = "PROVIDER_ERROR",
        **kwargs
    ):
        context = kwargs.get("context", {})
        context.update({
            "provider": provider,
            "status_code": status_code,
            "response_body": response_body[:500] if response_body else None  # Truncate long responses
        })
        kwargs["context"] = context
        
        super().__init__(message, error_code, **kwargs)
        self.provider = provider
        self.status_code = status_code
        self.response_body = response_body


class QualityAssuranceException(BusinessLogicException):
    """
    Exception for quality assurance failures.
    
    Raised when translation quality checks fail or quality thresholds are not met.
    """
    
    def __init__(
        self,
        message: str,
        quality_score: Optional[float] = None,
        quality_issues: Optional[List[str]] = None,
        threshold: Optional[float] = None,
        error_code: str = "QUALITY_ASSURANCE_ERROR",
        **kwargs
    ):
        context = kwargs.get("context", {})
        if quality_score is not None:
            context["quality_score"] = quality_score
        if quality_issues:
            context["quality_issues"] = quality_issues
        if threshold is not None:
            context["quality_threshold"] = threshold
        kwargs["context"] = context
        
        super().__init__(message, error_code, **kwargs)
        self.quality_score = quality_score
        self.quality_issues = quality_issues or []
        self.threshold = threshold


class ContentProcessingException(BusinessLogicException):
    """
    Exception for content processing errors.
    
    Handles errors during content chunking, context analysis,
    and content format processing.
    """
    
    def __init__(
        self,
        message: str,
        content_type: Optional[str] = None,
        processing_stage: Optional[str] = None,
        content_size: Optional[int] = None,
        error_code: str = "CONTENT_PROCESSING_ERROR",
        **kwargs
    ):
        context = kwargs.get("context", {})
        if content_type:
            context["content_type"] = content_type
        if processing_stage:
            context["processing_stage"] = processing_stage
        if content_size is not None:
            context["content_size"] = content_size
        kwargs["context"] = context
        
        super().__init__(message, error_code, **kwargs)
        self.content_type = content_type
        self.processing_stage = processing_stage
        self.content_size = content_size


class TranslationTimeoutException(TranslationException):
    """
    Raised when translation operations exceed timeout limits.
    """
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        elapsed_seconds: Optional[float] = None,
        error_code: str = "TRANSLATION_TIMEOUT",
        **kwargs
    ):
        context = kwargs.get("context", {})
        if timeout_seconds is not None:
            context["timeout_seconds"] = timeout_seconds
        if elapsed_seconds is not None:
            context["elapsed_seconds"] = elapsed_seconds
        kwargs["context"] = context
        
        super().__init__(message, error_code=error_code, **kwargs)
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds


class TranslationValidationException(TranslationException):
    """
    Raised when translation output validation fails.
    """
    
    def __init__(
        self,
        message: str,
        validation_type: Optional[str] = None,
        expected_format: Optional[str] = None,
        actual_format: Optional[str] = None,
        error_code: str = "TRANSLATION_VALIDATION_ERROR",
        **kwargs
    ):
        context = kwargs.get("context", {})
        if validation_type:
            context["validation_type"] = validation_type
        if expected_format:
            context["expected_format"] = expected_format
        if actual_format:
            context["actual_format"] = actual_format
        kwargs["context"] = context
        
        super().__init__(message, error_code=error_code, **kwargs)
        self.validation_type = validation_type
        self.expected_format = expected_format
        self.actual_format = actual_format