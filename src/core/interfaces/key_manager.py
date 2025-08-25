"""Key management interface"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class KeyStatus(str, Enum):
    """Status of an API key"""
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    EXPIRED = "expired"
    INVALID = "invalid"
    QUOTA_EXCEEDED = "quota_exceeded"
    SUSPENDED = "suspended"


@dataclass
class KeyInfo:
    """Information about an API key"""
    key_id: str  # Unique identifier (not the actual key)
    key_hash: str  # Hashed version of the key for logging
    status: KeyStatus
    provider_name: str
    
    # Usage tracking
    requests_made: int = 0
    tokens_used: int = 0
    last_used_at: Optional[datetime] = None
    
    # Rate limiting
    requests_per_minute: int = 60
    current_minute_requests: int = 0
    minute_window_start: Optional[datetime] = None
    
    # Error tracking
    consecutive_errors: int = 0
    last_error_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    
    # Metadata
    created_at: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def is_available(self) -> bool:
        """Check if key is available for use"""
        return (
            self.status == KeyStatus.ACTIVE
            and self.current_minute_requests < self.requests_per_minute
            and (self.next_retry_at is None or datetime.utcnow() >= self.next_retry_at)
        )
    
    @property
    def display_key(self) -> str:
        """Get a safe display version of the key"""
        return f"***{self.key_hash[-6:]}"


class KeyManager(ABC):
    """
    Abstract interface for managing API keys.
    
    Handles key rotation, rate limiting, error tracking, and availability.
    """
    
    @abstractmethod
    async def get_available_key(self, provider_name: str) -> Optional[KeyInfo]:
        """
        Get an available API key for the specified provider.
        
        Should return a key that:
        1. Is in ACTIVE status
        2. Has not exceeded rate limits
        3. Is not in retry backoff period
        
        Args:
            provider_name: Name of the provider needing a key
            
        Returns:
            KeyInfo if available, None if no keys are available
        """
        pass
    
    @abstractmethod
    async def report_key_success(
        self, 
        key_id: str, 
        tokens_used: Optional[int] = None
    ) -> None:
        """
        Report successful use of an API key.
        
        Args:
            key_id: ID of the key that was used successfully
            tokens_used: Number of tokens consumed (if available)
        """
        pass
    
    @abstractmethod
    async def report_key_error(
        self, 
        key_id: str, 
        error_type: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Report an error when using an API key.
        
        Should update key status and implement backoff logic based on error type.
        
        Args:
            key_id: ID of the key that encountered an error
            error_type: Type of error (rate_limit, invalid_key, quota_exceeded, etc.)
            error_details: Additional error information
        """
        pass
    
    @abstractmethod
    async def add_key(
        self, 
        provider_name: str, 
        api_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KeyInfo:
        """
        Add a new API key to the manager.
        
        Args:
            provider_name: Name of the provider this key belongs to
            api_key: The actual API key (will be hashed for storage)
            metadata: Additional metadata about the key
            
        Returns:
            KeyInfo for the newly added key
        """
        pass
    
    @abstractmethod
    async def remove_key(self, key_id: str) -> bool:
        """
        Remove an API key from the manager.
        
        Args:
            key_id: ID of the key to remove
            
        Returns:
            True if key was removed, False if key was not found
        """
        pass
    
    @abstractmethod
    async def get_key_stats(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about key usage.
        
        Args:
            provider_name: Optional provider to filter stats for
            
        Returns:
            Dictionary with key usage statistics
        """
        pass
    
    @abstractmethod
    async def refresh_key_status(self, key_id: str) -> KeyInfo:
        """
        Refresh the status of a specific key.
        
        May involve making a test request to verify key validity.
        
        Args:
            key_id: ID of the key to refresh
            
        Returns:
            Updated KeyInfo
        """
        pass
    
    @abstractmethod
    async def get_all_keys(self, provider_name: Optional[str] = None) -> List[KeyInfo]:
        """
        Get all keys, optionally filtered by provider.
        
        Args:
            provider_name: Optional provider to filter by
            
        Returns:
            List of all matching keys
        """
        pass
    
    async def cleanup_expired_keys(self) -> int:
        """
        Remove expired or permanently invalid keys.
        
        Default implementation does nothing.
        Implementations can override for automatic cleanup.
        
        Returns:
            Number of keys removed
        """
        return 0
    
    async def close(self) -> None:
        """
        Clean up key manager resources.
        
        Default implementation does nothing.
        Implementations should override if they need cleanup.
        """
        pass