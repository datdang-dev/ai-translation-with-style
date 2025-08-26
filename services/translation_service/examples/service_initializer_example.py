"""
Example script demonstrating how to use the ServiceInitializer class
"""

import asyncio
import json
import os
import sys

# Add the project root to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from services.translation_service.service_initializer import ServiceInitializer
from services.translation_service.translation_core import TranslationCore


def create_sample_config():
    """Create a sample configuration file for testing"""
    config = {
        "api_keys": ["sample-key-1", "sample-key-2"],
        "api_url": "https://openrouter.ai/api/v1/chat/completions",
        "max_retries": 3,
        "backoff_base": 2.0,
        "max_requests_per_minute": 20,
        "model": "openai/gpt-3.5-turbo"
    }
    
    with open("sample_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    return "sample_config.json"


async def example_basic_usage():
    """Example of basic usage of ServiceInitializer"""
    print("=== Basic ServiceInitializer Usage ===")
    
    # Create a sample config file
    config_path = create_sample_config()
    
    # Create service initializer
    initializer = ServiceInitializer(config_path)
    
    # Initialize all services at once
    api_key_manager, api_client, request_handler = initializer.initialize_all_services()
    
    print(f"API Key Manager initialized: {api_key_manager is not None}")
    print(f"API Client initialized: {api_client is not None}")
    print(f"Request Handler initialized: {request_handler is not None}")
    
    # Clean up
    os.remove(config_path)


async def example_individual_initialization():
    """Example of initializing services individually"""
    print("\n=== Individual Service Initialization ===")
    
    # Create a sample config file
    config_path = create_sample_config()
    
    # Create service initializer
    initializer = ServiceInitializer(config_path)
    
    # Initialize services one by one
    api_key_manager = initializer.initialize_api_key_manager()
    api_client = initializer.initialize_api_client()
    request_handler = initializer.initialize_request_handler()
    
    print(f"API Key Manager initialized: {api_key_manager is not None}")
    print(f"API Client initialized: {api_client is not None}")
    print(f"Request Handler initialized: {request_handler is not None}")
    
    # Get services using getter methods
    retrieved_key_manager = initializer.get_api_key_manager()
    retrieved_api_client = initializer.get_api_client()
    retrieved_request_handler = initializer.get_request_handler()
    
    print(f"Retrieved API Key Manager is same instance: {api_key_manager is retrieved_key_manager}")
    print(f"Retrieved API Client is same instance: {api_client is retrieved_api_client}")
    print(f"Retrieved Request Handler is same instance: {request_handler is retrieved_request_handler}")
    
    # Clean up
    os.remove(config_path)


async def example_with_translation_core():
    """Example of using ServiceInitializer with TranslationCore"""
    print("\n=== Using ServiceInitializer with TranslationCore ===")
    
    # Create a sample config file
    config_path = create_sample_config()
    
    # Create TranslationCore (which internally uses ServiceInitializer)
    translator = TranslationCore(config_path)
    
    print(f"TranslationCore API Key Manager initialized: {translator.api_key_manager is not None}")
    print(f"TranslationCore API Client initialized: {translator.api_client is not None}")
    print(f"TranslationCore Request Handler initialized: {translator.request_handler is not None}")
    
    # Clean up
    os.remove(config_path)


async def main():
    """Main function to run all examples"""
    await example_basic_usage()
    await example_individual_initialization()
    await example_with_translation_core()
    
    print("\n=== All examples completed successfully! ===")


if __name__ == "__main__":
    asyncio.run(main())