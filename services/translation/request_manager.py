"""
Request Manager
Handles API requests with retry logic and error handling
"""

import asyncio
import json
from typing import Dict, Any, Optional, Tuple, List
from services.common.logger import get_logger
from services.common.error_codes import ERR_RETRY_MAX_EXCEEDED, ERR_REQUEST_FAILED
from services.infrastructure.key_manager import APIKeyManager
from services.common.api_client import OpenRouterClient

class RequestManager:
    """Manages API requests with retry logic and key rotation"""
    
    def __init__(self, key_manager: APIKeyManager, api_url: str, config: Dict[str, Any]):
        """
        Initialize request manager
        :param key_manager: API key manager instance
        :param api_url: API endpoint URL
        :param config: Request configuration
        """
        self.key_manager = key_manager
        self.api_url = api_url
        self.config = config
        self.logger = get_logger("RequestManager")
        
        # Initialize API client
        self.api_client = OpenRouterClient(key_manager, api_url, self.logger)
        
        # Extract configuration
        self.max_retries = config.get("max_retries", 3)
        self.backoff_base = config.get("backoff_base", 2.0)
    
    async def send_request(self, data: Dict[str, Any]) -> Tuple[int, Optional[Dict[str, Any]]]:
        """
        Send a translation request with retry logic
        :param data: Request data to send
        :return: Tuple of (error_code, response)
        """
        self.logger.info("Starting translation request")
        
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                # Send request using API client
                response = await self.api_client.send_request(data)
                
                # Report successful key usage
                if hasattr(self.api_client, 'last_used_key'):
                    await self.key_manager.report_key_success(self.api_client.last_used_key)
                
                self.logger.info("Translation request completed successfully")
                return 0, response  # ERR_NONE
                
            except Exception as e:
                retry_count += 1
                self.logger.error(f"Request failed (attempt {retry_count}): {str(e)}")
                
                # Handle specific error types
                if hasattr(e, 'status_code'):
                    status_code = e.status_code
                    await self._handle_error_status(status_code, e)
                else:
                    # Generic error, treat as server error
                    await self._handle_error_status(500, e)
                
                if retry_count > self.max_retries:
                    self.logger.error(f"Max retries exceeded ({retry_count} attempts)")
                    return ERR_RETRY_MAX_EXCEEDED, None
                
                # Calculate backoff delay
                backoff_delay = self.backoff_base ** retry_count
                self.logger.info(f"Retrying in {backoff_delay:.1f}s (attempt {retry_count})")
                await asyncio.sleep(backoff_delay)
        
        return ERR_RETRY_MAX_EXCEEDED, None
    
    async def _handle_error_status(self, status_code: int, error: Exception) -> None:
        """
        Handle different HTTP status codes
        :param status_code: HTTP status code
        :param error: The error that occurred
        """
        if hasattr(self.api_client, 'last_used_key'):
            await self.key_manager.report_key_error(self.api_client.last_used_key, status_code)
        
        if status_code == 429:  # Rate limit
            self.logger.warning(f"Rate limit hit (429), will retry with backoff")
        elif 500 <= status_code < 600:  # Server error
            self.logger.warning(f"Server error ({status_code}), will retry with backoff")
        elif 400 <= status_code < 500:  # Client error
            self.logger.error(f"Client error ({status_code}): {str(error)}")
        else:
            self.logger.warning(f"Unexpected status code {status_code}: {str(error)}")
    
    async def send_batch_request(self, batch_data: List[Dict[str, Any]]) -> List[Tuple[int, Optional[Dict[str, Any]]]]:
        """
        Send multiple requests concurrently
        :param batch_data: List of request data
        :return: List of (error_code, response) tuples
        """
        self.logger.info(f"Sending batch request with {len(batch_data)} items")
        
        # Create tasks for concurrent execution
        tasks = [self.send_request(data) for data in batch_data]
        
        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Batch request failed with exception: {result}")
                processed_results.append((ERR_REQUEST_FAILED, None))
            else:
                processed_results.append(result)
        
        self.logger.info(f"Batch request completed: {len(processed_results)} results")
        return processed_results
    
    def get_request_stats(self) -> Dict[str, Any]:
        """
        Get request statistics
        :return: Dictionary with request statistics
        """
        return {
            "max_retries": self.max_retries,
            "backoff_base": self.backoff_base,
            "api_url": self.api_url,
            "key_manager_stats": self.key_manager.get_key_stats()
        }
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the API
        :return: True if healthy, False otherwise
        """
        try:
            # Simple health check request
            health_data = {
                "model": "google/gemini-2.0-flash-exp:free",  # Use a simple model for health check
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            error_code, response = await self.send_request(health_data)
            return error_code == 0
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False