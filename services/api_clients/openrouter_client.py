"""
OpenRouter API client implementation.
"""

import aiohttp
import json
from typing import Dict, Any

from ..core.interfaces import IAPIKeyManager, IMetricsService, IConfigurationService, Result
from ..core.exceptions import APIClientError
from .base_client import BaseAPIClient


class OpenRouterClient(BaseAPIClient):
    """OpenRouter API client implementation"""
    
    def __init__(self, 
                 key_manager: IAPIKeyManager,
                 metrics_service: IMetricsService,
                 config_service: IConfigurationService,
                 logger):
        
        api_config = config_service.get_api_config()
        super().__init__(key_manager, metrics_service, logger, api_config["timeout"])
        self.api_url = api_config["api_url"]
        self.config_service = config_service
    
    async def _make_request(self, 
                           url: str, 
                           headers: Dict[str, str], 
                           payload: Dict[str, Any]) -> Result:
        """Make HTTP request to OpenRouter API"""
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        try:
                            response_data = json.loads(response_text)
                            return Result.ok(response_data)
                        except json.JSONDecodeError as e:
                            return Result.error(500, f"Invalid JSON response: {str(e)}")
                    
                    else:
                        # Try to parse error response
                        try:
                            error_data = json.loads(response_text)
                            error_message = error_data.get("error", {}).get("message", response_text)
                        except json.JSONDecodeError:
                            error_message = response_text
                        
                        return Result.error(response.status, error_message)
                        
        except aiohttp.ClientTimeout:
            return Result.error(408, "Request timeout")
        except aiohttp.ClientError as e:
            return Result.error(503, f"Connection error: {str(e)}")
        except Exception as e:
            return Result.error(500, f"Unexpected error: {str(e)}")
    
    def _prepare_headers(self, api_key: str) -> Dict[str, str]:
        """Prepare OpenRouter request headers"""
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",  # Required by OpenRouter
            "X-Title": "Translation Service"  # Optional but recommended
        }
    
    def _get_api_url(self) -> str:
        """Get OpenRouter API URL"""
        return self.api_url


class APIClientFactory:
    """Factory for creating API clients"""
    
    @staticmethod
    def create_client(client_type: str,
                     key_manager: IAPIKeyManager,
                     metrics_service: IMetricsService,
                     config_service: IConfigurationService,
                     logger) -> BaseAPIClient:
        """Create API client based on type"""
        
        if client_type.lower() == "openrouter":
            return OpenRouterClient(key_manager, metrics_service, config_service, logger)
        elif client_type.lower() == "mock":
            # Import here to avoid circular imports
            from .base_client import MockAPIClient
            return MockAPIClient(key_manager, metrics_service, logger)
        else:
            raise ValueError(f"Unknown client type: {client_type}")
    
    @staticmethod
    def get_available_clients() -> list:
        """Get list of available client types"""
        return ["openrouter", "mock"]