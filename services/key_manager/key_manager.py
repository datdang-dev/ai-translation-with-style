import time
import asyncio
from typing import List, Dict, Optional

class KeyStatus:
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"

class APIKeyManager:
    def __init__(self, api_keys: List[str], max_retries: int = 3,
                 backoff_base: float = 2.0, max_requests_per_minute: int = 20):
        self.keys = [
            {
                'key': key,
                'name': f"key{i+1}",  # Simple name: key1, key2, etc.
                'status': KeyStatus.ACTIVE,
                'retry_count': 0,
                'last_used': None,
                'next_retry_time': 0,
                'timestamps': []
            } for i, key in enumerate(api_keys)
        ]
        self.current_index = 0
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.max_requests_per_minute = max_requests_per_minute
        self.lock = asyncio.Lock()

    async def get_next_available_key(self) -> Optional[Dict]:
        async with self.lock:
            now = time.time()
            for _ in range(len(self.keys)):
                key_info = self.keys[self.current_index]

                # clean timestamps older than 60s
                key_info['timestamps'] = [t for t in key_info['timestamps'] if now - t < 60]

                if key_info['status'] == KeyStatus.ACTIVE and len(key_info['timestamps']) < self.max_requests_per_minute and key_info['next_retry_time'] <= now:
                    key_info['timestamps'].append(now)
                    key_info['last_used'] = now
                    return key_info

                self._rotate_index()
            return None

    async def report_key_error(self, key: str, error_code: int):
        async with self.lock:
            now = time.time()
            for key_info in self.keys:
                if key_info['key'] == key:
                    # Rate limit detected
                    if error_code == 429:
                        key_info['retry_count'] += 1
                        if key_info['retry_count'] > self.max_retries:
                            key_info['status'] = KeyStatus.ERROR
                        else:
                            key_info['status'] = KeyStatus.RATE_LIMITED
                            key_info['next_retry_time'] = now + self.backoff_base ** key_info['retry_count']
                    # Server error (retryable)
                    elif 500 <= error_code < 600:
                        key_info['retry_count'] += 1
                        if key_info['retry_count'] > self.max_retries:
                            key_info['status'] = KeyStatus.ERROR
                        else:
                            key_info['status'] = KeyStatus.RATE_LIMITED
                            key_info['next_retry_time'] = now + self.backoff_base ** key_info['retry_count']
                    # Otherwise, mark active
                    else:
                        key_info['status'] = KeyStatus.ACTIVE
                        key_info['retry_count'] = 0
                        key_info['next_retry_time'] = 0
                    break

    def _rotate_index(self):
        self.current_index = (self.current_index + 1) % len(self.keys)
