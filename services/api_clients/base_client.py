"""
Base API client with common functionality.
"""

import time
import json
import asyncio
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from ..core.interfaces import IAPIClient, IAPIKeyManager, IMetricsService, Result
from ..core.exceptions import APIClientError, RateLimitError, ValidationError


class BaseAPIClient(IAPIClient, ABC):
    """Base class for API clients with common functionality"""
    
    def __init__(self, 
                 key_manager: IAPIKeyManager,
                 metrics_service: IMetricsService,
                 logger,
                 timeout: float = 30.0):
        self.key_manager = key_manager
        self.metrics_service = metrics_service
        self.logger = logger
        self.timeout = timeout
    
    @abstractmethod
    async def _make_request(self, 
                           url: str, 
                           headers: Dict[str, str], 
                           payload: Dict[str, Any]) -> Result:
        """Make actual HTTP request - to be implemented by subclasses"""
        pass
    
    @abstractmethod
    def _prepare_headers(self, api_key: str) -> Dict[str, str]:
        """Prepare request headers - to be implemented by subclasses"""
        pass
    
    @abstractmethod
    def _get_api_url(self) -> str:
        """Get API URL - to be implemented by subclasses"""
        pass
    
    async def send_request(self, data: Dict[str, Any]) -> Result:
        """Send API request with key management and error handling"""
        start_time = time.time()
        
        try:
            # Get available API key
            key_info = await self.key_manager.get_next_available_key()
            if not key_info:
                self.metrics_service.increment_counter("api.request.no_key_available")
                return Result.error(503, "No API keys available")
            
            api_key = key_info["key"]
            key_name = key_info["name"]
            
            # Prepare request
            url = self._get_api_url()
            headers = self._prepare_headers(api_key)
            
            self.logger.info(f"Sending request with key: {key_name}")
            
            # Make request
            result = await self._make_request(url, headers, data)
            
            # Record metrics
            duration = time.time() - start_time
            self.metrics_service.record_duration("api.request.duration", duration, {"key": key_name})
            
            if result.success:
                self.metrics_service.increment_counter("api.request.success", {"key": key_name})
                await self.key_manager.mark_key_success(key_name)
                self.logger.info(f"Request successful with key: {key_name}")
            else:
                self.metrics_service.increment_counter("api.request.error", {"key": key_name, "error_code": str(result.error_code)})
                await self._handle_error(key_name, result.error_code, result.error_message)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.metrics_service.record_duration("api.request.duration", duration, {"status": "exception"})
            self.metrics_service.increment_counter("api.request.exception")
            self.logger.error(f"Request exception: {str(e)}")
            return Result.error(500, f"Request failed: {str(e)}")
    
    async def _handle_error(self, key_name: str, error_code: int, error_message: str) -> None:
        """Handle API errors and update key status"""
        if error_code == 429:  # Rate limit
            await self.key_manager.mark_key_status(key_name, "rate_limited")
            self.logger.warning(f"Rate limit hit for key: {key_name}")
        elif 500 <= error_code < 600:  # Server errors
            await self.key_manager.mark_key_status(key_name, "error")
            self.logger.error(f"Server error {error_code} for key: {key_name}")
        elif 400 <= error_code < 500:  # Client errors
            await self.key_manager.mark_key_status(key_name, "error")
            self.logger.error(f"Client error {error_code} for key: {key_name}")
        else:
            self.logger.error(f"Unknown error {error_code} for key: {key_name}: {error_message}")


class MockAPIClient(BaseAPIClient):
    """Mock API client for testing without real API calls"""
    
    def __init__(self, 
                 key_manager: IAPIKeyManager,
                 metrics_service: IMetricsService,
                 logger,
                 timeout: float = 30.0,
                 simulate_errors: bool = False,
                 error_rate: float = 0.1):
        super().__init__(key_manager, metrics_service, logger, timeout)
        self.simulate_errors = simulate_errors
        self.error_rate = error_rate
        self.request_count = 0
    
    async def _make_request(self, 
                           url: str, 
                           headers: Dict[str, str], 
                           payload: Dict[str, Any]) -> Result:
        """Mock HTTP request"""
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        self.request_count += 1
        
        # Simulate errors if configured
        if self.simulate_errors and (self.request_count % 10) < (self.error_rate * 10):
            if self.request_count % 20 == 0:
                return Result.error(429, "Rate limit exceeded")
            elif self.request_count % 15 == 0:
                return Result.error(500, "Internal server error")
            else:
                return Result.error(400, "Bad request")
        
        # Simulate successful response
        mock_response = {
            "id": f"mock-response-{self.request_count}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Mock translation response for request {self.request_count}"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        
        return Result.ok(mock_response)
    
    def _prepare_headers(self, api_key: str) -> Dict[str, str]:
        """Prepare mock headers"""
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "MockTranslationClient/1.0"
        }
    
    def _get_api_url(self) -> str:
        """Get mock API URL"""
        return "https://mock-api.example.com/v1/chat/completions"