"""Retry handling with exponential backoff and jitter"""

import asyncio
import random
import time
from typing import Optional, Callable, Any, Type, Tuple, List
from dataclasses import dataclass
from enum import Enum

from ..observability import get_logger


class RetryableError(Exception):
    """Base class for retryable errors"""
    pass


class RetryStrategy(str, Enum):
    """Retry strategies"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    
    # Which exceptions to retry on
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        RetryableError,
        asyncio.TimeoutError,
        ConnectionError,
        OSError,
    )
    
    # HTTP status codes to retry on
    retryable_status_codes: List[int] = None
    
    def __post_init__(self):
        if self.retryable_status_codes is None:
            self.retryable_status_codes = [429, 500, 502, 503, 504]


class RetryHandler:
    """
    Handles retry logic with configurable strategies and observability.
    
    Supports:
    - Exponential backoff with jitter
    - Linear backoff
    - Fixed delay
    - Custom retry conditions
    - Detailed logging and metrics
    """
    
    def __init__(self, config: RetryConfig):
        """
        Initialize retry handler.
        
        Args:
            config: Retry configuration
        """
        self.config = config
        self.logger = get_logger("retry_handler")
    
    async def execute_with_retry(
        self,
        operation: Callable[[], Any],
        operation_name: str = "operation",
        custom_retry_condition: Optional[Callable[[Exception], bool]] = None
    ) -> Any:
        """
        Execute an operation with retry logic.
        
        Args:
            operation: Async operation to execute
            operation_name: Name for logging purposes
            custom_retry_condition: Custom function to determine if error is retryable
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: The last exception if all retries are exhausted
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):  # +1 for initial attempt
            try:
                self.logger.debug(
                    f"Executing {operation_name}",
                    attempt=attempt + 1,
                    max_attempts=self.config.max_retries + 1
                )
                
                result = await operation()
                
                if attempt > 0:
                    self.logger.info(
                        f"{operation_name} succeeded after retries",
                        attempt=attempt + 1,
                        total_attempts=attempt + 1
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if this is the last attempt
                if attempt >= self.config.max_retries:
                    self.logger.error(
                        f"{operation_name} failed after all retries",
                        total_attempts=attempt + 1,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    raise
                
                # Check if error is retryable
                if not self._is_retryable_error(e, custom_retry_condition):
                    self.logger.warning(
                        f"{operation_name} failed with non-retryable error",
                        attempt=attempt + 1,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    raise
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt)
                
                self.logger.warning(
                    f"{operation_name} failed, retrying",
                    attempt=attempt + 1,
                    max_attempts=self.config.max_retries + 1,
                    error=str(e),
                    error_type=type(e).__name__,
                    retry_delay_seconds=delay
                )
                
                # Wait before retry
                await asyncio.sleep(delay)
        
        # This should never be reached due to the raise in the loop
        raise last_exception
    
    def _is_retryable_error(
        self, 
        error: Exception,
        custom_condition: Optional[Callable[[Exception], bool]] = None
    ) -> bool:
        """
        Determine if an error is retryable.
        
        Args:
            error: Exception to check
            custom_condition: Custom retry condition function
            
        Returns:
            True if error is retryable
        """
        # Check custom condition first
        if custom_condition:
            try:
                if custom_condition(error):
                    return True
            except Exception as e:
                self.logger.warning(
                    "Custom retry condition failed",
                    error=str(e)
                )
        
        # Check if it's a configured retryable exception type
        if isinstance(error, self.config.retryable_exceptions):
            return True
        
        # Check HTTP status codes if it's an HTTP error
        if hasattr(error, 'status_code') and error.status_code:
            return error.status_code in self.config.retryable_status_codes
        
        # Check if it has a retryable property
        if hasattr(error, 'is_retryable'):
            return error.is_retryable
        
        return False
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        if self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.initial_delay_seconds
            
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.initial_delay_seconds * (attempt + 1)
            
        else:  # EXPONENTIAL_BACKOFF
            delay = self.config.initial_delay_seconds * (
                self.config.exponential_base ** attempt
            )
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay_seconds)
        
        # Apply jitter if enabled
        if self.config.jitter:
            # Add random jitter (±25% of delay)
            jitter_range = delay * 0.25
            jitter = random.uniform(-jitter_range, jitter_range)
            delay = max(0.1, delay + jitter)  # Ensure minimum 0.1s delay
        
        return delay
    
    def create_http_retry_condition(self) -> Callable[[Exception], bool]:
        """
        Create a retry condition specifically for HTTP errors.
        
        Returns:
            Function that determines if HTTP error is retryable
        """
        def is_http_retryable(error: Exception) -> bool:
            # Import here to avoid circular imports
            from .async_client import HTTPError
            
            if isinstance(error, HTTPError):
                return error.is_retryable
            
            return False
        
        return is_http_retryable
    
    def create_provider_retry_condition(self) -> Callable[[Exception], bool]:
        """
        Create a retry condition for provider-specific errors.
        
        Returns:
            Function that determines if provider error is retryable
        """
        def is_provider_retryable(error: Exception) -> bool:
            # Rate limiting is always retryable
            if hasattr(error, 'status_code') and error.status_code == 429:
                return True
            
            # Server errors are retryable
            if hasattr(error, 'status_code') and error.status_code >= 500:
                return True
            
            # Network errors are retryable
            if isinstance(error, (ConnectionError, OSError, asyncio.TimeoutError)):
                return True
            
            # Check error message for known retryable patterns
            error_msg = str(error).lower()
            retryable_patterns = [
                'timeout',
                'connection',
                'network',
                'rate limit',
                'server error',
                'service unavailable',
                'bad gateway',
                'gateway timeout'
            ]
            
            return any(pattern in error_msg for pattern in retryable_patterns)
        
        return is_provider_retryable


class RetryableOperation:
    """
    Decorator for making operations retryable.
    
    Usage:
        @RetryableOperation(RetryConfig(max_retries=3))
        async def my_operation():
            # operation code
    """
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.retry_handler = RetryHandler(config)
    
    def __call__(self, func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            async def operation():
                return await func(*args, **kwargs)
            
            return await self.retry_handler.execute_with_retry(
                operation,
                operation_name=func.__name__
            )
        
        return wrapper


# Convenience functions for common retry configurations

def create_http_retry_handler(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0
) -> RetryHandler:
    """Create a retry handler optimized for HTTP requests"""
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay_seconds=initial_delay,
        max_delay_seconds=max_delay,
        exponential_base=2.0,
        jitter=True,
        retryable_status_codes=[429, 500, 502, 503, 504]
    )
    return RetryHandler(config)


def create_provider_retry_handler(
    max_retries: int = 5,
    initial_delay: float = 2.0,
    max_delay: float = 300.0
) -> RetryHandler:
    """Create a retry handler optimized for AI provider calls"""
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay_seconds=initial_delay,
        max_delay_seconds=max_delay,
        exponential_base=2.0,
        jitter=True,
        retryable_status_codes=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524]
    )
    return RetryHandler(config)


async def retry_with_backoff(
    operation: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    operation_name: str = "operation"
) -> Any:
    """
    Simple retry function with exponential backoff.
    
    Args:
        operation: Async operation to retry
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        operation_name: Name for logging
        
    Returns:
        Result of the operation
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay_seconds=initial_delay,
        max_delay_seconds=max_delay
    )
    
    handler = RetryHandler(config)
    return await handler.execute_with_retry(operation, operation_name)