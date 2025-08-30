"""
API Key Manager
Handles API key rotation, rate limiting, and error tracking
"""

import time
import asyncio
from typing import List, Dict, Optional, Any
from services.common.logger import get_logger

class KeyStatus:
    """API key status constants"""
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    EXHAUSTED = "exhausted"

class APIKeyManager:
    """Manages API keys with rotation, rate limiting, and error handling"""
    
    def __init__(self, api_keys: List[str], max_retries: int = 3,
                 backoff_base: float = 2.0, max_requests_per_minute: int = 20):
        """
        Initialize API key manager
        :param api_keys: List of API keys
        :param max_retries: Maximum retry attempts per key
        :param backoff_base: Base value for exponential backoff
        :param max_requests_per_minute: Rate limit per key per minute
        """
        self.keys = [
            {
                'key': key,
                'name': f"key{i+1}",
                'status': KeyStatus.ACTIVE,
                'retry_count': 0,
                'last_used': None,
                'next_retry_time': 0,
                'timestamps': [],
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0
            } for i, key in enumerate(api_keys)
        ]
        self.current_index = 0
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.max_requests_per_minute = max_requests_per_minute
        self.lock = asyncio.Lock()
        self.logger = get_logger("APIKeyManager")
        
        if not api_keys:
            self.logger.warning("No API keys provided")
        else:
            self.logger.info(f"Initialized with {len(api_keys)} API keys")
    
    async def get_next_available_key(self) -> Optional[Dict]:
        """
        Get the next available API key
        :return: Key info dictionary or None if no keys available
        """
        async with self.lock:
            now = time.time()
            
            # Try all keys to find an available one
            for _ in range(len(self.keys)):
                key_info = self.keys[self.current_index]
                
                # Clean old timestamps (older than 60 seconds)
                key_info['timestamps'] = [t for t in key_info['timestamps'] if now - t < 60]
                
                # Check if key is available
                if (key_info['status'] == KeyStatus.ACTIVE and 
                    len(key_info['timestamps']) < self.max_requests_per_minute and 
                    key_info['next_retry_time'] <= now):
                    
                    # Mark key as used
                    key_info['timestamps'].append(now)
                    key_info['last_used'] = now
                    key_info['total_requests'] += 1
                    
                    self.logger.debug(f"Using key: {key_info['name']}")
                    return key_info
                
                # Move to next key
                self._rotate_index()
            
            # No keys available
            self.logger.warning("No available API keys")
            return None
    
    async def report_key_success(self, key: str) -> None:
        """
        Report successful API key usage
        :param key: The API key that was successful
        """
        async with self.lock:
            for key_info in self.keys:
                if key_info['key'] == key:
                    key_info['successful_requests'] += 1
                    key_info['retry_count'] = 0  # Reset retry count on success
                    if key_info['status'] != KeyStatus.ACTIVE:
                        key_info['status'] = KeyStatus.ACTIVE
                        self.logger.info(f"Key {key_info['name']} restored to active status")
                    break
    
    async def report_key_error(self, key: str, error_code: int) -> None:
        """
        Report API key error and update status
        :param key: The API key that had an error
        :param error_code: HTTP error code
        """
        async with self.lock:
            now = time.time()
            
            for key_info in self.keys:
                if key_info['key'] == key:
                    key_info['failed_requests'] += 1
                    
                    # Handle different error types
                    if error_code == 429:  # Rate limit
                        key_info['retry_count'] += 1
                        if key_info['retry_count'] > self.max_retries:
                            key_info['status'] = KeyStatus.EXHAUSTED
                            self.logger.error(f"Key {key_info['name']} exhausted after {self.max_retries} rate limit errors")
                        else:
                            key_info['status'] = KeyStatus.RATE_LIMITED
                            backoff_time = self.backoff_base ** key_info['retry_count']
                            key_info['next_retry_time'] = now + backoff_time
                            self.logger.warning(f"Key {key_info['name']} rate limited, retry in {backoff_time:.1f}s")
                    
                    elif 500 <= error_code < 600:  # Server error (retryable)
                        key_info['retry_count'] += 1
                        if key_info['retry_count'] > self.max_retries:
                            key_info['status'] = KeyStatus.ERROR
                            self.logger.error(f"Key {key_info['name']} marked as error after {self.max_retries} server errors")
                        else:
                            key_info['status'] = KeyStatus.RATE_LIMITED
                            backoff_time = self.backoff_base ** key_info['retry_count']
                            key_info['next_retry_time'] = now + backoff_time
                            self.logger.warning(f"Key {key_info['name']} server error, retry in {backoff_time:.1f}s")
                    
                    else:  # Other errors, keep key active
                        key_info['status'] = KeyStatus.ACTIVE
                        key_info['retry_count'] = 0
                        key_info['next_retry_time'] = 0
                        self.logger.warning(f"Key {key_info['name']} had error {error_code}, keeping active")
                    break
    
    def _rotate_index(self) -> None:
        """Rotate to the next key index"""
        self.current_index = (self.current_index + 1) % len(self.keys)
    
    def get_key_stats(self) -> Dict[str, Any]:
        """Get statistics about all API keys"""
        total_keys = len(self.keys)
        active_keys = sum(1 for k in self.keys if k['status'] == KeyStatus.ACTIVE)
        rate_limited_keys = sum(1 for k in self.keys if k['status'] == KeyStatus.RATE_LIMITED)
        error_keys = sum(1 for k in self.keys if k['status'] == KeyStatus.ERROR)
        exhausted_keys = sum(1 for k in self.keys if k['status'] == KeyStatus.EXHAUSTED)
        
        total_requests = sum(k['total_requests'] for k in self.keys)
        successful_requests = sum(k['successful_requests'] for k in self.keys)
        failed_requests = sum(k['failed_requests'] for k in self.keys)
        
        return {
            'total_keys': total_keys,
            'active_keys': active_keys,
            'rate_limited_keys': rate_limited_keys,
            'error_keys': error_keys,
            'exhausted_keys': exhausted_keys,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0
        }
    
    def reset_key(self, key: str) -> bool:
        """
        Reset a key to active status
        :param key: The API key to reset
        :return: True if key was found and reset, False otherwise
        """
        for key_info in self.keys:
            if key_info['key'] == key:
                key_info['status'] = KeyStatus.ACTIVE
                key_info['retry_count'] = 0
                key_info['next_retry_time'] = 0
                self.logger.info(f"Key {key_info['name']} reset to active status")
                return True
        return False