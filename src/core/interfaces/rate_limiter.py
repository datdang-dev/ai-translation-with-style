"""Rate limiting interface"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta


class RateLimitResult(str, Enum):
    """Result of a rate limit check"""
    ALLOWED = "allowed"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"


@dataclass
class RateLimitInfo:
    """Information about current rate limit status"""
    result: RateLimitResult
    
    # Current usage
    current_requests: int
    current_tokens: int
    
    # Limits
    request_limit: Optional[int] = None
    token_limit: Optional[int] = None
    
    # Timing
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    reset_at: Optional[datetime] = None
    retry_after_seconds: Optional[int] = None
    
    # Additional info
    remaining_requests: Optional[int] = None
    remaining_tokens: Optional[int] = None
    
    @property
    def is_allowed(self) -> bool:
        """Check if request is allowed"""
        return self.result == RateLimitResult.ALLOWED
    
    @property
    def should_retry(self) -> bool:
        """Check if request should be retried later"""
        return self.result == RateLimitResult.RATE_LIMITED
    
    @property
    def time_until_reset(self) -> Optional[timedelta]:
        """Get time until rate limit resets"""
        if self.reset_at:
            now = datetime.utcnow()
            if self.reset_at > now:
                return self.reset_at - now
        return None


class RateLimiter(ABC):
    """
    Abstract interface for rate limiting.
    
    Handles request and token-based rate limiting with configurable windows
    and backoff strategies.
    """
    
    @abstractmethod
    async def check_rate_limit(
        self, 
        key: str,
        estimated_tokens: Optional[int] = None
    ) -> RateLimitInfo:
        """
        Check if a request is allowed under current rate limits.
        
        Args:
            key: Unique identifier for the entity being rate limited
            estimated_tokens: Estimated tokens that will be consumed
            
        Returns:
            RateLimitInfo indicating if request is allowed and current status
        """
        pass
    
    @abstractmethod
    async def record_request(
        self, 
        key: str,
        tokens_used: Optional[int] = None,
        success: bool = True
    ) -> None:
        """
        Record a completed request for rate limiting purposes.
        
        Args:
            key: Unique identifier for the entity
            tokens_used: Actual tokens consumed
            success: Whether the request was successful
        """
        pass
    
    @abstractmethod
    async def get_current_usage(self, key: str) -> Dict[str, Any]:
        """
        Get current usage statistics for a key.
        
        Args:
            key: Unique identifier to get stats for
            
        Returns:
            Dictionary with current usage information
        """
        pass
    
    @abstractmethod
    async def reset_limits(self, key: str) -> None:
        """
        Reset rate limits for a specific key.
        
        Useful for testing or manual intervention.
        
        Args:
            key: Unique identifier to reset limits for
        """
        pass
    
    @abstractmethod
    async def update_limits(
        self, 
        key: str,
        requests_per_minute: Optional[int] = None,
        requests_per_hour: Optional[int] = None,
        tokens_per_minute: Optional[int] = None,
        tokens_per_hour: Optional[int] = None
    ) -> None:
        """
        Update rate limits for a specific key.
        
        Args:
            key: Unique identifier to update limits for
            requests_per_minute: New requests per minute limit
            requests_per_hour: New requests per hour limit  
            tokens_per_minute: New tokens per minute limit
            tokens_per_hour: New tokens per hour limit
        """
        pass
    
    async def wait_if_needed(self, key: str, max_wait_seconds: int = 60) -> bool:
        """
        Wait if rate limited, up to max_wait_seconds.
        
        Default implementation checks rate limits and waits if needed.
        
        Args:
            key: Unique identifier to check
            max_wait_seconds: Maximum time to wait
            
        Returns:
            True if request can proceed, False if wait time exceeds max
        """
        import asyncio
        
        rate_info = await self.check_rate_limit(key)
        
        if rate_info.is_allowed:
            return True
        
        if not rate_info.should_retry:
            return False
        
        wait_time = rate_info.retry_after_seconds or 1
        if wait_time > max_wait_seconds:
            return False
        
        await asyncio.sleep(wait_time)
        return True
    
    async def close(self) -> None:
        """
        Clean up rate limiter resources.
        
        Default implementation does nothing.
        Implementations should override if they need cleanup.
        """
        pass