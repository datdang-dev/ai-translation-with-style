"""
Enhanced API key manager using composition of specialized services.
"""

import time
import asyncio
from typing import Optional, Dict, Any

from ..core.interfaces import IAPIKeyManager, IConfigurationService
from ..core.exceptions import APIKeyError
from .key_rotation_service import KeyRotationService, APIKey, KeyStatus
from .quota_tracker import QuotaTracker
from .backoff_strategy import BackoffStrategy


class EnhancedAPIKeyManager(IAPIKeyManager):
    """Enhanced API key manager with separated concerns"""
    
    def __init__(self, config_service: IConfigurationService):
        self.config_service = config_service
        self.key_rotation = KeyRotationService(config_service)
        self.quota_tracker = QuotaTracker(config_service)
        self.backoff_strategy = BackoffStrategy(config_service)
        
        self.max_retries = config_service.get("max_retries", 3)
    
    async def get_next_available_key(self) -> Optional[Dict[str, Any]]:
        """Get next available API key that can make a request"""
        attempts = 0
        max_attempts = len(await self.key_rotation.get_all_keys()) * 2  # Give each key 2 chances
        
        while attempts < max_attempts:
            # Get next key from rotation
            api_key = await self.key_rotation.get_next_available_key()
            if not api_key:
                return None  # No active keys available
            
            # Check if key is in backoff period
            if not await self.backoff_strategy.should_retry(api_key.name):
                attempts += 1
                continue
            
            # Check quota limits
            if not await self.quota_tracker.can_make_request(api_key.name):
                # Mark as rate limited temporarily
                await self.key_rotation.mark_key_status(api_key.name, KeyStatus.RATE_LIMITED)
                attempts += 1
                continue
            
            # Record the request attempt
            now = time.time()
            await self.quota_tracker.record_request(api_key.name)
            await self.key_rotation.mark_key_used(api_key.name, now)
            
            return {
                "key": api_key.key,
                "name": api_key.name,
                "status": api_key.status.value,
                "last_used": api_key.last_used,
                "requests_remaining": (await self.quota_tracker.get_quota_stats()).get(api_key.name, {}).get("requests_remaining", 0)
            }
            
        return None  # No suitable key found
    
    async def mark_key_status(self, key_name: str, status: str) -> None:
        """Mark key status and handle backoff if needed"""
        key_status = KeyStatus(status)
        await self.key_rotation.mark_key_status(key_name, key_status)
        
        # Handle backoff for rate limited or error status
        if key_status in [KeyStatus.RATE_LIMITED, KeyStatus.ERROR]:
            # Get retry count for this key
            retry_info = await self.backoff_strategy.get_retry_info(key_name)
            retry_count = retry_info["retry_count"]
            
            if retry_count < self.max_retries:
                await self.backoff_strategy.schedule_retry(key_name)
            else:
                # Max retries exceeded, disable key temporarily
                await self.key_rotation.mark_key_status(key_name, KeyStatus.DISABLED)
    
    async def mark_key_success(self, key_name: str) -> None:
        """Mark key as successful (reset backoff)"""
        await self.backoff_strategy.reset_backoff(key_name)
        await self.key_rotation.mark_key_status(key_name, KeyStatus.ACTIVE)
    
    async def get_manager_stats(self) -> Dict[str, Any]:
        """Get comprehensive manager statistics"""
        key_stats = await self.key_rotation.get_key_stats()
        quota_stats = await self.quota_tracker.get_quota_stats()
        backoff_stats = await self.backoff_strategy.get_backoff_stats()
        
        return {
            "keys": key_stats,
            "quotas": quota_stats,
            "backoffs": backoff_stats,
            "summary": {
                "total_keys": key_stats["total_keys"],
                "active_keys": key_stats["active_keys"],
                "rate_limited_keys": key_stats["rate_limited_keys"],
                "error_keys": key_stats["error_keys"],
                "keys_in_backoff": len([k for k, v in backoff_stats.items() if v["in_backoff"]])
            }
        }
    
    async def reset_all_keys(self) -> None:
        """Reset all keys to active status (emergency recovery)"""
        all_keys = await self.key_rotation.get_all_keys()
        for key in all_keys:
            await self.key_rotation.reset_key_status(key.name)
            await self.backoff_strategy.reset_backoff(key.name)
            await self.quota_tracker.clear_key_history(key.name)