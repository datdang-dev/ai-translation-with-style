"""Key management implementation with rotation and rate limiting"""

import asyncio
import hashlib
import time
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

from ..core.interfaces import KeyManager, KeyInfo, KeyStatus
from .observability import get_logger


class InMemoryKeyManager(KeyManager):
    """
    In-memory implementation of key management.
    
    Features:
    - API key rotation and load balancing
    - Rate limiting per key
    - Error tracking and backoff
    - Health monitoring
    - Thread-safe operations
    """
    
    def __init__(self):
        self.logger = get_logger("key_manager")
        self._keys: Dict[str, KeyInfo] = {}
        self._keys_by_provider: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()
        self._current_indices: Dict[str, int] = {}  # Round-robin indices per provider
    
    async def add_key(
        self, 
        provider_name: str, 
        api_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KeyInfo:
        """Add a new API key to the manager"""
        async with self._lock:
            # Create key hash for identification
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            key_id = f"{provider_name}_{key_hash[:12]}"
            
            # Check if key already exists
            if key_id in self._keys:
                self.logger.warning(f"Key already exists: {key_id}")
                return self._keys[key_id]
            
            # Create KeyInfo
            key_info = KeyInfo(
                key_id=key_id,
                key_hash=key_hash,
                status=KeyStatus.ACTIVE,
                provider_name=provider_name,
                created_at=datetime.now(timezone.utc),
                metadata=metadata or {}
            )
            
            # Store the actual key securely (in production, use proper key storage)
            key_info.metadata['_api_key'] = api_key
            
            # Add to collections
            self._keys[key_id] = key_info
            
            if provider_name not in self._keys_by_provider:
                self._keys_by_provider[provider_name] = []
                self._current_indices[provider_name] = 0
            
            self._keys_by_provider[provider_name].append(key_id)
            
            self.logger.info(
                f"Added API key for provider {provider_name}",
                key_id=key_id,
                provider=provider_name
            )
            
            return key_info
    
    async def get_available_key(self, provider_name: str) -> Optional[KeyInfo]:
        """Get an available API key for the specified provider"""
        async with self._lock:
            if provider_name not in self._keys_by_provider:
                self.logger.warning(f"No keys configured for provider: {provider_name}")
                return None
            
            provider_keys = self._keys_by_provider[provider_name]
            if not provider_keys:
                return None
            
            # Try to find an available key using round-robin
            start_index = self._current_indices[provider_name]
            
            for i in range(len(provider_keys)):
                index = (start_index + i) % len(provider_keys)
                key_id = provider_keys[index]
                key_info = self._keys[key_id]
                
                if key_info.is_available:
                    # Update round-robin index for next call
                    self._current_indices[provider_name] = (index + 1) % len(provider_keys)
                    
                    # Update usage tracking
                    now = datetime.now(timezone.utc)
                    
                    # Reset minute window if needed
                    if (key_info.minute_window_start is None or 
                        now - key_info.minute_window_start >= timedelta(minutes=1)):
                        key_info.minute_window_start = now
                        key_info.current_minute_requests = 0
                    
                    # Increment request count
                    key_info.current_minute_requests += 1
                    key_info.requests_made += 1
                    key_info.last_used_at = now
                    
                    self.logger.debug(
                        f"Selected key for {provider_name}",
                        key_id=key_id,
                        requests_this_minute=key_info.current_minute_requests,
                        total_requests=key_info.requests_made
                    )
                    
                    return key_info
            
            self.logger.warning(f"No available keys for provider: {provider_name}")
            return None
    
    async def report_key_success(
        self, 
        key_id: str, 
        tokens_used: Optional[int] = None
    ) -> None:
        """Report successful use of an API key"""
        async with self._lock:
            key_info = self._keys.get(key_id)
            if not key_info:
                self.logger.warning(f"Unknown key ID: {key_id}")
                return
            
            # Reset error tracking on success
            key_info.consecutive_errors = 0
            key_info.next_retry_at = None
            
            # Update token usage
            if tokens_used:
                key_info.tokens_used += tokens_used
            
            # Ensure key is active if it was in error state
            if key_info.status in [KeyStatus.RATE_LIMITED, KeyStatus.SUSPENDED]:
                key_info.status = KeyStatus.ACTIVE
                self.logger.info(f"Key {key_id} restored to active status")
            
            self.logger.debug(
                f"Reported success for key {key_id}",
                tokens_used=tokens_used,
                total_tokens=key_info.tokens_used
            )
    
    async def report_key_error(
        self, 
        key_id: str, 
        error_type: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Report an error when using an API key"""
        async with self._lock:
            key_info = self._keys.get(key_id)
            if not key_info:
                self.logger.warning(f"Unknown key ID: {key_id}")
                return
            
            key_info.consecutive_errors += 1
            key_info.last_error_at = datetime.now(timezone.utc)
            
            # Handle different error types
            if error_type == "rate_limit":
                key_info.status = KeyStatus.RATE_LIMITED
                # Backoff for rate limiting (exponential backoff)
                backoff_seconds = min(60 * (2 ** (key_info.consecutive_errors - 1)), 3600)
                key_info.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
                
                self.logger.warning(
                    f"Key {key_id} rate limited",
                    backoff_seconds=backoff_seconds,
                    consecutive_errors=key_info.consecutive_errors
                )
                
            elif error_type == "invalid_key":
                key_info.status = KeyStatus.INVALID
                self.logger.error(f"Key {key_id} is invalid")
                
            elif error_type == "quota_exceeded":
                key_info.status = KeyStatus.QUOTA_EXCEEDED
                # Backoff for 24 hours on quota exceeded
                key_info.next_retry_at = datetime.now(timezone.utc) + timedelta(hours=24)
                self.logger.error(f"Key {key_id} quota exceeded")
                
            else:
                # Generic error handling
                if key_info.consecutive_errors >= 5:
                    key_info.status = KeyStatus.SUSPENDED
                    # Suspend for increasing durations
                    backoff_seconds = min(300 * key_info.consecutive_errors, 7200)  # Max 2 hours
                    key_info.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
                    
                    self.logger.error(
                        f"Key {key_id} suspended due to consecutive errors",
                        consecutive_errors=key_info.consecutive_errors,
                        backoff_seconds=backoff_seconds
                    )
                else:
                    # Short backoff for temporary errors
                    backoff_seconds = 30 * key_info.consecutive_errors
                    key_info.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
            
            self.logger.warning(
                f"Reported error for key {key_id}",
                error_type=error_type,
                consecutive_errors=key_info.consecutive_errors,
                status=key_info.status.value,
                error_details=error_details
            )
    
    async def remove_key(self, key_id: str) -> bool:
        """Remove an API key from the manager"""
        async with self._lock:
            key_info = self._keys.pop(key_id, None)
            if not key_info:
                return False
            
            # Remove from provider list
            provider_keys = self._keys_by_provider.get(key_info.provider_name, [])
            if key_id in provider_keys:
                provider_keys.remove(key_id)
            
            self.logger.info(f"Removed key {key_id}")
            return True
    
    async def get_key_stats(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about key usage"""
        async with self._lock:
            if provider_name:
                # Stats for specific provider
                provider_keys = self._keys_by_provider.get(provider_name, [])
                keys = [self._keys[key_id] for key_id in provider_keys]
            else:
                # Stats for all keys
                keys = list(self._keys.values())
            
            if not keys:
                return {"total_keys": 0}
            
            # Calculate statistics
            total_requests = sum(key.requests_made for key in keys)
            total_tokens = sum(key.tokens_used for key in keys)
            
            status_counts = {}
            for status in KeyStatus:
                status_counts[status.value] = sum(1 for key in keys if key.status == status)
            
            active_keys = [key for key in keys if key.status == KeyStatus.ACTIVE]
            avg_requests_per_key = total_requests / len(keys) if keys else 0
            
            return {
                "total_keys": len(keys),
                "active_keys": len(active_keys),
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "average_requests_per_key": avg_requests_per_key,
                "status_distribution": status_counts,
                "provider": provider_name
            }
    
    async def refresh_key_status(self, key_id: str) -> KeyInfo:
        """Refresh the status of a specific key"""
        async with self._lock:
            key_info = self._keys.get(key_id)
            if not key_info:
                raise ValueError(f"Key not found: {key_id}")
            
            now = datetime.now(timezone.utc)
            
            # Check if backoff period has expired
            if key_info.next_retry_at and now >= key_info.next_retry_at:
                if key_info.status in [KeyStatus.RATE_LIMITED, KeyStatus.SUSPENDED]:
                    key_info.status = KeyStatus.ACTIVE
                    key_info.next_retry_at = None
                    key_info.consecutive_errors = 0
                    self.logger.info(f"Key {key_id} status refreshed to active")
            
            # Reset minute window if needed
            if (key_info.minute_window_start is None or 
                now - key_info.minute_window_start >= timedelta(minutes=1)):
                key_info.minute_window_start = now
                key_info.current_minute_requests = 0
            
            return key_info
    
    async def get_all_keys(self, provider_name: Optional[str] = None) -> List[KeyInfo]:
        """Get all keys, optionally filtered by provider"""
        async with self._lock:
            if provider_name:
                provider_keys = self._keys_by_provider.get(provider_name, [])
                return [self._keys[key_id] for key_id in provider_keys]
            else:
                return list(self._keys.values())
    
    async def cleanup_expired_keys(self) -> int:
        """Remove expired or permanently invalid keys"""
        async with self._lock:
            keys_to_remove = []
            
            for key_id, key_info in self._keys.items():
                # Remove permanently invalid keys
                if key_info.status in [KeyStatus.INVALID, KeyStatus.EXPIRED]:
                    keys_to_remove.append(key_id)
                
                # Remove keys that have been suspended for too long
                elif (key_info.status == KeyStatus.SUSPENDED and 
                      key_info.last_error_at and
                      datetime.now(timezone.utc) - key_info.last_error_at > timedelta(days=7)):
                    keys_to_remove.append(key_id)
            
            # Remove the keys
            for key_id in keys_to_remove:
                await self.remove_key(key_id)
            
            if keys_to_remove:
                self.logger.info(f"Cleaned up {len(keys_to_remove)} expired keys")
            
            return len(keys_to_remove)
    
    def get_api_key(self, key_id: str) -> Optional[str]:
        """Get the actual API key (for internal use only)"""
        key_info = self._keys.get(key_id)
        if key_info and '_api_key' in key_info.metadata:
            return key_info.metadata['_api_key']
        return None