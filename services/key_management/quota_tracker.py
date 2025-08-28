"""
Quota tracker service - handles API key quota and rate limiting.
"""

import time
import asyncio
from typing import Dict, List
from collections import defaultdict, deque

from ..core.interfaces import IConfigurationService


class QuotaTracker:
    """Tracks API key quotas and rate limits"""
    
    def __init__(self, config_service: IConfigurationService):
        self.config_service = config_service
        self.max_requests_per_minute = config_service.get("max_requests_per_minute", 20)
        
        # Track timestamps of requests for each key
        self._request_timestamps: Dict[str, deque] = defaultdict(lambda: deque())
        self._lock = asyncio.Lock()
    
    async def can_make_request(self, key_name: str) -> bool:
        """Check if key can make a request without hitting rate limit"""
        async with self._lock:
            now = time.time()
            timestamps = self._request_timestamps[key_name]
            
            # Remove timestamps older than 1 minute
            while timestamps and now - timestamps[0] > 60:
                timestamps.popleft()
            
            # Check if we're under the rate limit
            return len(timestamps) < self.max_requests_per_minute
    
    async def record_request(self, key_name: str) -> None:
        """Record a request for rate limiting"""
        async with self._lock:
            now = time.time()
            self._request_timestamps[key_name].append(now)
    
    async def get_requests_in_last_minute(self, key_name: str) -> int:
        """Get number of requests made in the last minute"""
        async with self._lock:
            now = time.time()
            timestamps = self._request_timestamps[key_name]
            
            # Remove old timestamps
            while timestamps and now - timestamps[0] > 60:
                timestamps.popleft()
            
            return len(timestamps)
    
    async def get_time_until_next_request(self, key_name: str) -> float:
        """Get seconds until next request can be made"""
        async with self._lock:
            now = time.time()
            timestamps = self._request_timestamps[key_name]
            
            if not timestamps or len(timestamps) < self.max_requests_per_minute:
                return 0.0
            
            # Calculate time until oldest request expires
            oldest_request = timestamps[0]
            time_until_available = 60 - (now - oldest_request)
            return max(0.0, time_until_available)
    
    async def clear_key_history(self, key_name: str) -> None:
        """Clear request history for a key"""
        async with self._lock:
            if key_name in self._request_timestamps:
                self._request_timestamps[key_name].clear()
    
    async def get_quota_stats(self) -> Dict[str, Dict[str, int]]:
        """Get quota statistics for all keys"""
        async with self._lock:
            stats = {}
            now = time.time()
            
            for key_name, timestamps in self._request_timestamps.items():
                # Clean old timestamps
                while timestamps and now - timestamps[0] > 60:
                    timestamps.popleft()
                
                stats[key_name] = {
                    "requests_last_minute": len(timestamps),
                    "requests_remaining": max(0, self.max_requests_per_minute - len(timestamps)),
                    "quota_percentage": (len(timestamps) / self.max_requests_per_minute) * 100
                }
            
            return stats