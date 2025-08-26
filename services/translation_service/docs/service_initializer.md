# ServiceInitializer Class Documentation

The `ServiceInitializer` class is responsible for initializing the core components of the translation service with proper dependency injection. It handles the creation and configuration of the API key manager, API client, and request handler.

## Overview

The `ServiceInitializer` class provides a clean and consistent way to initialize the services required by the translation system. It ensures that all dependencies are properly injected and that services are only initialized once.

## Class Definition

```python
class ServiceInitializer:
    def __init__(self, config_path: str, logger=None):
        # Initialize the service initializer with configuration
        pass
    
    def initialize_api_key_manager(self, api_keys: Optional[List[str]] = None) -> APIKeyManager:
        # Initialize the API key manager
        pass
    
    def initialize_api_client(self, api_key_manager: Optional[APIKeyManager] = None) -> OpenRouterClient:
        # Initialize the API client
        pass
    
    def initialize_request_handler(self, 
                                 api_client: Optional[OpenRouterClient] = None,
                                 api_key_manager: Optional[APIKeyManager] = None) -> RequestHandler:
        # Initialize the request handler
        pass
    
    def initialize_all_services(self) -> tuple[APIKeyManager, OpenRouterClient, RequestHandler]:
        # Initialize all services in the correct order
        pass
    
    def get_api_key_manager(self) -> Optional[APIKeyManager]:
        # Get the initialized API key manager
        pass
    
    def get_api_client(self) -> Optional[OpenRouterClient]:
        # Get the initialized API client
        pass
    
    def get_request_handler(self) -> Optional[RequestHandler]:
        # Get the initialized request handler
        pass
```

## Usage Examples

### Basic Usage

```python
from services.translation_service.service_initializer import ServiceInitializer

# Create service initializer
initializer = ServiceInitializer("config.json")

# Initialize all services at once
api_key_manager, api_client, request_handler = initializer.initialize_all_services()
```

### Individual Service Initialization

```python
from services.translation_service.service_initializer import ServiceInitializer

# Create service initializer
initializer = ServiceInitializer("config.json")

# Initialize services one by one
api_key_manager = initializer.initialize_api_key_manager()
api_client = initializer.initialize_api_client()
request_handler = initializer.initialize_request_handler()
```

### Custom API Keys

```python
from services.translation_service.service_initializer import ServiceInitializer

# Create service initializer
initializer = ServiceInitializer("config.json")

# Initialize with custom API keys
custom_keys = ["key1", "key2", "key3"]
api_key_manager = initializer.initialize_api_key_manager(custom_keys)
```

## Dependencies

The `ServiceInitializer` class depends on the following components:

1. **APIKeyManager** - Manages API keys and their rotation
2. **OpenRouterClient** - Handles communication with the OpenRouter API
3. **RequestHandler** - Manages request processing and error handling

## Configuration

The service initializer expects a JSON configuration file with the following structure:

```json
{
  "api_keys": ["key1", "key2"],
  "api_url": "https://openrouter.ai/api/v1/chat/completions",
  "max_retries": 3,
  "backoff_base": 2.0,
  "max_requests_per_minute": 20
}
```

If no API keys are provided in the configuration, the service initializer will attempt to load them from `config/api_keys.json`.

## Best Practices

1. **Singleton Pattern**: The service initializer ensures that each service is only initialized once, returning the same instance on subsequent calls.

2. **Proper Dependency Order**: When initializing services individually, make sure to initialize dependencies in the correct order:
   - API Key Manager first
   - API Client second (depends on API Key Manager)
   - Request Handler last (depends on both API Key Manager and API Client)

3. **Error Handling**: The service initializer will raise appropriate exceptions if required configuration is missing or invalid.

## Integration with TranslationCore

The `TranslationCore` class internally uses the `ServiceInitializer` to set up its dependencies:

```python
class TranslationCore:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = get_logger("TranslationCore")
        self.api_key_manager = None
        self.api_client = None
        self.request_handler = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize required services using ServiceInitializer"""
        service_initializer = ServiceInitializer(self.config_path, self.logger)
        self.api_key_manager, self.api_client, self.request_handler = service_initializer.initialize_all_services()
```

This ensures consistent initialization across the application.