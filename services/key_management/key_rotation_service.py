"""
Key rotation service - handles cycling through available API keys.
"""

import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..core.interfaces import IConfigurationService
from ..core.exceptions import APIKeyError


class KeyStatus(Enum):
    """API key status"""
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class APIKey:
    """API key data structure"""
    key: str
    name: str
    status: KeyStatus = KeyStatus.ACTIVE
    last_used: Optional[float] = None
    error_count: int = 0
    total_requests: int = 0


class KeyRotationService:
    """Handles API key rotation and status management"""
    
    def __init__(self, config_service: IConfigurationService):
        self.config_service = config_service
        self._keys: List[APIKey] = []
        self._current_index = 0
        self._lock = asyncio.Lock()
        self._initialize_keys()
    
    def _initialize_keys(self) -> None:
        """Initialize API keys from configuration"""
        api_keys = self.config_service.get_api_keys()
        if not api_keys:
            raise APIKeyError("No API keys configured")
        
        self._keys = [
            APIKey(
                key=key,
                name=f"key{i+1}",
                status=KeyStatus.ACTIVE
            )
            for i, key in enumerate(api_keys)
        ]
    
    async def get_next_available_key(self) -> Optional[APIKey]:
        """Get the next available API key"""
        async with self._lock:
            # Try to find an active key starting from current index
            attempts = 0
            while attempts < len(self._keys):
                key = self._keys[self._current_index]
                
                if key.status == KeyStatus.ACTIVE:
                    # Move to next key for next request
                    self._current_index = (self._current_index + 1) % len(self._keys)
                    return key
                
                # Move to next key and try again
                self._current_index = (self._current_index + 1) % len(self._keys)
                attempts += 1
            
            return None  # No active keys available
    
    async def mark_key_status(self, key_name: str, status: KeyStatus, error_message: str = None) -> None:
        """Mark key status"""
        async with self._lock:
            for key in self._keys:
                if key.name == key_name:
                    key.status = status
                    if status == KeyStatus.ERROR:
                        key.error_count += 1
                    break
    
    async def mark_key_used(self, key_name: str, timestamp: float) -> None:
        """Mark key as used"""
        async with self._lock:
            for key in self._keys:
                if key.name == key_name:
                    key.last_used = timestamp
                    key.total_requests += 1
                    break
    
    async def reset_key_status(self, key_name: str) -> None:
        """Reset key status to active"""
        await self.mark_key_status(key_name, KeyStatus.ACTIVE)
    
    async def get_key_stats(self) -> Dict[str, Any]:
        """Get key statistics"""
        async with self._lock:
            stats = {
                "total_keys": len(self._keys),
                "active_keys": sum(1 for k in self._keys if k.status == KeyStatus.ACTIVE),
                "rate_limited_keys": sum(1 for k in self._keys if k.status == KeyStatus.RATE_LIMITED),
                "error_keys": sum(1 for k in self._keys if k.status == KeyStatus.ERROR),
                "keys": [
                    {
                        "name": key.name,
                        "status": key.status.value,
                        "last_used": key.last_used,
                        "error_count": key.error_count,
                        "total_requests": key.total_requests
                    }
                    for key in self._keys
                ]
            }
            return stats
    
    async def get_all_keys(self) -> List[APIKey]:
        """Get all keys (for testing/debugging)"""
        async with self._lock:
            return self._keys.copy()