"""
Backoff strategy service - handles retry timing and backoff calculations.
"""

import time
import asyncio
import random
from typing import Dict, Optional
from enum import Enum

from ..core.interfaces import IConfigurationService


class BackoffType(Enum):
    """Types of backoff strategies"""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"
    JITTERED = "jittered"


class BackoffStrategy:
    """Handles backoff timing for failed requests"""
    
    def __init__(self, config_service: IConfigurationService):
        self.config_service = config_service
        self.base_delay = config_service.get("backoff_base", 2.0)
        self.max_delay = config_service.get("max_backoff_delay", 300.0)  # 5 minutes max
        self.backoff_type = BackoffType(config_service.get("backoff_type", "exponential"))
        
        # Track retry times for each key
        self._retry_times: Dict[str, float] = {}
        self._retry_counts: Dict[str, int] = {}
        self._lock = asyncio.Lock()
    
    async def should_retry(self, key_name: str) -> bool:
        """Check if key should be retried (not in backoff period)"""
        async with self._lock:
            if key_name not in self._retry_times:
                return True
            
            now = time.time()
            return now >= self._retry_times[key_name]
    
    async def calculate_backoff_delay(self, key_name: str, attempt: int) -> float:
        """Calculate backoff delay for a key"""
        async with self._lock:
            if self.backoff_type == BackoffType.EXPONENTIAL:
                delay = self.base_delay * (2 ** attempt)
            elif self.backoff_type == BackoffType.LINEAR:
                delay = self.base_delay * attempt
            elif self.backoff_type == BackoffType.FIXED:
                delay = self.base_delay
            elif self.backoff_type == BackoffType.JITTERED:
                # Exponential with jitter to prevent thundering herd
                base_delay = self.base_delay * (2 ** attempt)
                jitter = random.uniform(0.5, 1.5)
                delay = base_delay * jitter
            else:
                delay = self.base_delay
            
            # Cap at max delay
            return min(delay, self.max_delay)
    
    async def schedule_retry(self, key_name: str, delay: float = None) -> None:
        """Schedule a retry for a key"""
        async with self._lock:
            if delay is None:
                retry_count = self._retry_counts.get(key_name, 0)
                delay = await self.calculate_backoff_delay(key_name, retry_count)
            
            now = time.time()
            self._retry_times[key_name] = now + delay
            self._retry_counts[key_name] = self._retry_counts.get(key_name, 0) + 1
    
    async def reset_backoff(self, key_name: str) -> None:
        """Reset backoff for a key (after successful request)"""
        async with self._lock:
            self._retry_times.pop(key_name, None)
            self._retry_counts.pop(key_name, None)
    
    async def get_retry_info(self, key_name: str) -> Dict[str, Optional[float]]:
        """Get retry information for a key"""
        async with self._lock:
            now = time.time()
            retry_time = self._retry_times.get(key_name)
            
            return {
                "retry_count": self._retry_counts.get(key_name, 0),
                "next_retry_time": retry_time,
                "seconds_until_retry": max(0, retry_time - now) if retry_time else 0,
                "can_retry_now": retry_time is None or now >= retry_time
            }
    
    async def get_backoff_stats(self) -> Dict[str, Dict]:
        """Get backoff statistics for all keys"""
        async with self._lock:
            stats = {}
            now = time.time()
            
            for key_name in set(list(self._retry_times.keys()) + list(self._retry_counts.keys())):
                retry_time = self._retry_times.get(key_name)
                stats[key_name] = {
                    "retry_count": self._retry_counts.get(key_name, 0),
                    "in_backoff": retry_time is not None and now < retry_time,
                    "seconds_until_retry": max(0, retry_time - now) if retry_time else 0
                }
            
            return stats