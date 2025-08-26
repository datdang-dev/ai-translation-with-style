"""
Service initializer for translation service components
Handles initialization of API key manager, API client, and request handler with proper dependency injection
"""

import json
from typing import List, Dict, Any, Optional

from services.key_manager.key_manager import APIKeyManager
from services.common.api_client import OpenRouterClient
from services.request_handler.request_handler import RequestHandler
from services.common.logger import get_logger


class ServiceInitializer:
    """Handles initialization of translation service components with dependency injection"""
    
    def __init__(self, config_path: str, logger=None):
        """
        Initialize ServiceInitializer
        :param config_path: Path to the configuration file
        :param logger: Optional logger instance
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = logger or get_logger("ServiceInitializer")
        self._api_key_manager: Optional[APIKeyManager] = None
        self._api_client: Optional[OpenRouterClient] = None
        self._request_handler: Optional[RequestHandler] = None
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to read configuration file: {e}")
            raise
    
    def initialize_api_key_manager(self, api_keys: Optional[List[str]] = None) -> APIKeyManager:
        """
        Initialize API key manager
        :param api_keys: Optional list of API keys, if not provided will be loaded from config
        :return: Initialized APIKeyManager instance
        """
        if self._api_key_manager is not None:
            return self._api_key_manager
            
        # Load API keys from config if not provided
        if api_keys is None:
            api_keys = self.config.get("api_keys", [])
            
        # If no API keys in config, try to load from external file
        if not api_keys:
            api_keys_path = "config/api_keys.json"
            try:
                with open(api_keys_path, 'r', encoding='utf-8') as f:
                    api_keys_config = json.load(f)
                    loaded_api_keys = api_keys_config.get("api_keys", [])
                self.logger.info(f"Loaded {len(loaded_api_keys)} API keys from {api_keys_path}")
                api_keys = loaded_api_keys
            except FileNotFoundError:
                self.logger.warning(f"API keys file not found at {api_keys_path}")
                api_keys = []
            except Exception as e:
                self.logger.error(f"Error loading API keys: {e}")
                api_keys = []
        
        if not api_keys:
            self.logger.error("No API keys available. Please configure API keys in config/api_keys.json")
            raise ValueError("No API keys available")
        
        # Get configuration parameters
        max_retries = self.config.get("max_retries", 3)
        backoff_base = self.config.get("backoff_base", 2.0)
        max_requests_per_minute = self.config.get("max_requests_per_minute", 20)
        
        # Initialize and store API key manager
        self._api_key_manager = APIKeyManager(
            api_keys,
            max_retries=max_retries,
            backoff_base=backoff_base,
            max_requests_per_minute=max_requests_per_minute
        )
        
        return self._api_key_manager
    
    def initialize_api_client(self, api_key_manager: Optional[APIKeyManager] = None) -> OpenRouterClient:
        """
        Initialize API client
        :param api_key_manager: Optional APIKeyManager instance, if not provided will use initialized one
        :return: Initialized OpenRouterClient instance
        """
        if self._api_client is not None:
            return self._api_client
            
        # Get or initialize API key manager
        if api_key_manager is None:
            api_key_manager = self._api_key_manager or self.initialize_api_key_manager()
            
        # Get API URL from config
        api_url = self.config.get("api_url", "https://openrouter.ai/api/v1/chat/completions")
        
        # Initialize and store API client
        self._api_client = OpenRouterClient(api_key_manager, api_url, self.logger)
        
        return self._api_client
    
    def initialize_request_handler(self, 
                                 api_client: Optional[OpenRouterClient] = None,
                                 api_key_manager: Optional[APIKeyManager] = None) -> RequestHandler:
        """
        Initialize request handler
        :param api_client: Optional OpenRouterClient instance, if not provided will use initialized one
        :param api_key_manager: Optional APIKeyManager instance, if not provided will use initialized one
        :return: Initialized RequestHandler instance
        """
        if self._request_handler is not None:
            return self._request_handler
            
        # Get or initialize dependencies
        if api_client is None:
            api_client = self._api_client or self.initialize_api_client()
            
        if api_key_manager is None:
            api_key_manager = self._api_key_manager or self.initialize_api_key_manager()
        
        # Create handler configuration
        handler_config = {
            "max_retries": self.config.get("max_retries", 3),
            "backoff_base": self.config.get("backoff_base", 2.0)
        }
        
        # Initialize and store request handler
        self._request_handler = RequestHandler(
            api_client,
            api_key_manager,
            self.logger,
            handler_config
        )
        
        return self._request_handler
    
    def initialize_all_services(self) -> tuple[APIKeyManager, OpenRouterClient, RequestHandler]:
        """
        Initialize all services in the correct order
        :return: Tuple of (api_key_manager, api_client, request_handler)
        """
        # Initialize in correct order: key manager -> api client -> request handler
        api_key_manager = self.initialize_api_key_manager()
        api_client = self.initialize_api_client(api_key_manager)
        request_handler = self.initialize_request_handler(api_client, api_key_manager)
        
        return api_key_manager, api_client, request_handler
    
    def get_api_key_manager(self) -> Optional[APIKeyManager]:
        """Get initialized API key manager"""
        return self._api_key_manager
    
    def get_api_client(self) -> Optional[OpenRouterClient]:
        """Get initialized API client"""
        return self._api_client
    
    def get_request_handler(self) -> Optional[RequestHandler]:
        """Get initialized request handler"""
        return self._request_handler