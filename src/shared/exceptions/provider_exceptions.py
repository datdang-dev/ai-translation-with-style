"""
Provider-specific exception classes.

These exceptions handle specific provider error scenarios including
connection issues, authentication failures, rate limiting, and timeouts.
"""

from typing import Optional, Dict, Any
from .base_exceptions import InfrastructureException


class ProviderConnectionException(InfrastructureException):
    """
    Raised when connection to a translation provider fails.
    
    This includes network connectivity issues, DNS resolution failures,
    and connection timeouts.
    """
    
    def __init__(
        self,
        message: str,
        provider: str,
        endpoint: Optional[str] = None,
        connection_timeout: Optional[float] = None,
        error_code: str = "PROVIDER_CONNECTION_ERROR",
        **kwargs
    ):
        context = kwargs.get("context", {})
        context.update({
            "provider": provider,
            "endpoint": endpoint,
            "connection_timeout": connection_timeout
        })
        kwargs["context"] = context
        
        super().__init__(message, error_code, **kwargs)
        self.provider = provider
        self.endpoint = endpoint
        self.connection_timeout = connection_timeout


class ProviderAuthenticationException(InfrastructureException):
    """
    Raised when authentication with a provider fails.
    
    This includes invalid API keys, expired tokens, insufficient permissions,
    or authentication service failures.
    """
    
    def __init__(
        self,
        message: str,
        provider: str,
        auth_method: Optional[str] = None,
        key_identifier: Optional[str] = None,
        error_code: str = "PROVIDER_AUTH_ERROR",
        **kwargs
    ):
        context = kwargs.get("context", {})
        context.update({
            "provider": provider,
            "auth_method": auth_method,
            "key_identifier": key_identifier  # Masked key identifier for debugging
        })
        kwargs["context"] = context
        
        super().__init__(message, error_code, **kwargs)
        self.provider = provider
        self.auth_method = auth_method
        self.key_identifier = key_identifier


class ProviderRateLimitException(InfrastructureException):
    """
    Raised when provider rate limits are exceeded.
    
    Includes information about rate limit quotas, reset times,
    and retry strategies.
    """
    
    def __init__(
        self,
        message: str,
        provider: str,
        rate_limit_type: Optional[str] = None,  # 'requests_per_minute', 'tokens_per_day', etc.
        quota_limit: Optional[int] = None,
        quota_remaining: Optional[int] = None,
        reset_time: Optional[int] = None,  # Unix timestamp
        retry_after: Optional[int] = None,  # Seconds to wait
        error_code: str = "PROVIDER_RATE_LIMIT_ERROR",
        **kwargs
    ):
        context = kwargs.get("context", {})
        context.update({
            "provider": provider,
            "rate_limit_type": rate_limit_type,
            "quota_limit": quota_limit,
            "quota_remaining": quota_remaining,
            "reset_time": reset_time,
            "retry_after": retry_after
        })
        kwargs["context"] = context
        
        super().__init__(message, error_code, **kwargs)
        self.provider = provider
        self.rate_limit_type = rate_limit_type
        self.quota_limit = quota_limit
        self.quota_remaining = quota_remaining
        self.reset_time = reset_time
        self.retry_after = retry_after


class ProviderTimeoutException(InfrastructureException):
    """
    Raised when provider operations exceed timeout limits.
    
    This includes read timeouts, request timeouts, and response timeouts.
    """
    
    def __init__(
        self,
        message: str,
        provider: str,
        timeout_type: Optional[str] = None,  # 'connect', 'read', 'total'
        timeout_seconds: Optional[float] = None,
        elapsed_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        error_code: str = "PROVIDER_TIMEOUT_ERROR",
        **kwargs
    ):
        context = kwargs.get("context", {})
        context.update({
            "provider": provider,
            "timeout_type": timeout_type,
            "timeout_seconds": timeout_seconds,
            "elapsed_seconds": elapsed_seconds,
            "operation": operation
        })
        kwargs["context"] = context
        
        super().__init__(message, error_code, **kwargs)
        self.provider = provider
        self.timeout_type = timeout_type
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds
        self.operation = operation


class ProviderServiceUnavailableException(InfrastructureException):
    """
    Raised when a provider service is temporarily unavailable.
    
    This includes maintenance windows, service outages, and capacity issues.
    """
    
    def __init__(
        self,
        message: str,
        provider: str,
        service_status: Optional[str] = None,
        estimated_recovery: Optional[str] = None,
        error_code: str = "PROVIDER_SERVICE_UNAVAILABLE",
        **kwargs
    ):
        context = kwargs.get("context", {})
        context.update({
            "provider": provider,
            "service_status": service_status,
            "estimated_recovery": estimated_recovery
        })
        kwargs["context"] = context
        
        super().__init__(message, error_code, **kwargs)
        self.provider = provider
        self.service_status = service_status
        self.estimated_recovery = estimated_recovery


class ProviderQuotaExceededException(InfrastructureException):
    """
    Raised when provider usage quotas are exceeded.
    
    This includes daily/monthly usage limits, token quotas, or credit limitations.
    """
    
    def __init__(
        self,
        message: str,
        provider: str,
        quota_type: Optional[str] = None,  # 'tokens', 'requests', 'credits'
        quota_limit: Optional[int] = None,
        quota_used: Optional[int] = None,
        quota_period: Optional[str] = None,  # 'daily', 'monthly', 'total'
        quota_reset: Optional[str] = None,
        error_code: str = "PROVIDER_QUOTA_EXCEEDED",
        **kwargs
    ):
        context = kwargs.get("context", {})
        context.update({
            "provider": provider,
            "quota_type": quota_type,
            "quota_limit": quota_limit,
            "quota_used": quota_used,
            "quota_period": quota_period,
            "quota_reset": quota_reset
        })
        kwargs["context"] = context
        
        super().__init__(message, error_code, **kwargs)
        self.provider = provider
        self.quota_type = quota_type
        self.quota_limit = quota_limit
        self.quota_used = quota_used
        self.quota_period = quota_period
        self.quota_reset = quota_reset