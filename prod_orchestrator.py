"""
Production translation orchestrator with real API keys.
"""

import asyncio
import json
import time
import sys
import os
from typing import Dict, Any, Optional

from services.core.interfaces import *
from services.core.dependency_container import DIContainer
from services.core.configuration_service import ConfigurationService
from services.key_management.enhanced_key_manager import EnhancedAPIKeyManager
from services.monitoring.metrics_service import MetricsService, TimedOperation
from services.resilience.circuit_breaker import CircuitBreakerManager
from services.common.logger import get_logger

# Import the real OpenRouter client
try:
    from services.api_clients.openrouter_client import APIClientFactory
    HAS_AIOHTTP = True
except ImportError:
    print("⚠️  Warning: aiohttp not installed. Install with: pip install aiohttp")
    print("Falling back to mock client for demo...")
    from services.api_clients.base_client import MockAPIClient
    HAS_AIOHTTP = False


class ProductionTranslationOrchestrator:
    """Production translation orchestrator with real API integration"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.logger = get_logger("ProductionOrchestrator")
        self._setup_services()
    
    def _setup_services(self) -> None:
        """Setup services for production use"""
        # Create DI container
        self.container = DIContainer()
        
        # Register configuration service
        try:
            config_service = ConfigurationService(self.config_path)
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
        
        self.container.register_singleton(IConfigurationService, config_service)
        
        # Check if API keys are configured
        api_keys = config_service.get_api_keys()
        if not api_keys or api_keys == ["your-openrouter-api-key-1", "your-openrouter-api-key-2", "your-openrouter-api-key-3"]:
            self.logger.error("❌ No valid API keys configured!")
            print("\n🔑 API Key Setup Required:")
            print("1. Copy config/api_keys.json.template to config/api_keys.json")
            print("2. Replace placeholder keys with your real OpenRouter API keys")
            print("3. Get API keys from: https://openrouter.ai/keys")
            sys.exit(1)
        
        print(f"✅ Loaded {len(api_keys)} API key(s)")
        
        # Register metrics service
        metrics_service = MetricsService()
        self.container.register_singleton(IMetricsService, metrics_service)
        
        # Register enhanced key manager
        key_manager = EnhancedAPIKeyManager(config_service)
        self.container.register_singleton(IAPIKeyManager, key_manager)
        
        # Register circuit breaker manager
        circuit_breaker_manager = CircuitBreakerManager(config_service)
        self.container.register_singleton(CircuitBreakerManager, circuit_breaker_manager)
        
        # Register API client
        client_type = config_service.get("client_type", "openrouter")
        
        if client_type == "openrouter" and HAS_AIOHTTP:
            api_client = APIClientFactory.create_client(
                "openrouter", key_manager, metrics_service, config_service, self.logger
            )
            print("✅ Using real OpenRouter API client")
        else:
            # Fallback to mock for testing
            api_client = MockAPIClient(
                key_manager, metrics_service, self.logger,
                simulate_errors=False, error_rate=0.0
            )
            print("⚠️  Using mock API client (install aiohttp for real API)")
        
        self.container.register_singleton(IAPIClient, api_client)
        
        # Store references
        self.config_service = config_service
        self.metrics_service = metrics_service
        self.key_manager = key_manager
        self.circuit_breaker_manager = circuit_breaker_manager
        self.api_client = api_client
    
    async def translate_text(self, text: str) -> Result:
        """Translate text using production API"""
        
        with TimedOperation(self.metrics_service, "translation.request"):
            # Prepare request data
            messages = self.config_service.get("messages", [])
            processed_messages = []
            
            for msg in messages:
                content = msg["content"].replace("{text}", text)
                processed_messages.append({
                    "role": msg["role"],
                    "content": content
                })
            
            request_data = {
                "model": self.config_service.get("model"),
                "messages": processed_messages,
                "temperature": self.config_service.get("temperature", 0.3),
                "max_tokens": self.config_service.get("max_tokens", 2000)
            }
            
            self.logger.info(f"Translating: {text[:100]}...")
            
            # Use circuit breaker for API call
            result = await self.circuit_breaker_manager.call_with_breaker(
                "api_client",
                self.api_client.send_request,
                request_data
            )
            
            if result.success:
                self.metrics_service.increment_counter("translation.success")
                
                # Extract translated text from response
                try:
                    response_data = result.data
                    translated_text = response_data["choices"][0]["message"]["content"]
                    
                    # Log token usage if available
                    if "usage" in response_data:
                        usage = response_data["usage"]
                        self.metrics_service.record_value("tokens.prompt", usage.get("prompt_tokens", 0))
                        self.metrics_service.record_value("tokens.completion", usage.get("completion_tokens", 0))
                        self.metrics_service.record_value("tokens.total", usage.get("total_tokens", 0))
                        self.logger.info(f"Token usage: {usage.get('total_tokens', 0)} total")
                    
                    self.logger.info("✅ Translation completed successfully")
                    return Result.ok({
                        "translated_text": translated_text, 
                        "original_text": text,
                        "usage": response_data.get("usage", {})
                    })
                    
                except (KeyError, IndexError) as e:
                    self.logger.error(f"Failed to extract translation: {e}")
                    return Result.error(500, "Invalid response format")
            else:
                self.metrics_service.increment_counter("translation.error")
                self.logger.error(f"❌ Translation failed: {result.error_message}")
                return result
    
    async def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed production status"""
        
        # Get comprehensive stats
        key_stats = await self.key_manager.get_manager_stats()
        circuit_stats = await self.circuit_breaker_manager.get_all_statuses()
        metrics = self.metrics_service.get_metrics()
        
        # Calculate success rate
        success_count = self.metrics_service.get_counter("translation.success") or 0
        error_count = self.metrics_service.get_counter("translation.error") or 0
        total_requests = success_count + error_count
        success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate token usage
        total_tokens = 0
        if "tokens.total" in metrics["histograms"]:
            token_stats = metrics["histograms"]["tokens.total"]["stats"]
            if token_stats:
                total_tokens = token_stats["sum"]
        
        return {
            "timestamp": time.time(),
            "service_status": "healthy" if key_stats["summary"]["active_keys"] > 0 else "degraded",
            "performance": {
                "total_requests": total_requests,
                "successful_requests": success_count,
                "failed_requests": error_count,
                "success_rate_percent": round(success_rate, 2),
                "total_tokens_used": int(total_tokens)
            },
            "key_management": key_stats,
            "circuit_breakers": circuit_stats,
            "configuration": {
                "model": self.config_service.get("model"),
                "client_type": self.config_service.get("client_type"),
                "max_concurrent": self.config_service.get("batch.max_concurrent"),
                "api_keys_count": len(self.config_service.get_api_keys())
            }
        }


async def main():
    """Production demo with real API keys"""
    print("🚀 Production Translation Service")
    print("=" * 50)
    
    # Check if API keys file exists
    if not os.path.exists("config/api_keys.json"):
        print("❌ API keys file not found!")
        print("\n📋 Setup Instructions:")
        print("1. Copy the template: cp config/api_keys.json.template config/api_keys.json")
        print("2. Edit config/api_keys.json with your real API keys")
        print("3. Get OpenRouter API keys from: https://openrouter.ai/keys")
        print("\nExample api_keys.json:")
        print('{\n  "api_keys": [\n    "sk-or-v1-your-key-here"\n  ]\n}')
        return
    
    try:
        # Initialize orchestrator
        orchestrator = ProductionTranslationOrchestrator("config/production_config.json")
        
        # Test translations
        test_texts = [
            "Hello, how are you today?",
            "This is a test of the translation service.",
            "The weather is beautiful this morning."
        ]
        
        print(f"\n📝 Testing with {len(test_texts)} sample texts...")
        
        for i, text in enumerate(test_texts, 1):
            print(f"\n{i}. Translating: '{text}'")
            
            result = await orchestrator.translate_text(text)
            
            if result.success:
                translation = result.data["translated_text"]
                usage = result.data.get("usage", {})
                print(f"   ✅ Result: {translation}")
                if usage:
                    print(f"   📊 Tokens: {usage.get('total_tokens', 0)} total")
            else:
                print(f"   ❌ Error: {result.error_message}")
            
            # Small delay between requests
            await asyncio.sleep(1)
        
        # Show final status
        print(f"\n📊 Final Status:")
        status = await orchestrator.get_detailed_status()
        perf = status["performance"]
        print(f"   📈 Success Rate: {perf['success_rate_percent']}%")
        print(f"   🔢 Total Requests: {perf['total_requests']}")
        print(f"   🪙 Total Tokens: {perf['total_tokens_used']}")
        print(f"   🔑 Active Keys: {status['key_management']['summary']['active_keys']}")
        
        # Show key usage details
        key_details = status['key_management']['keys']['keys']
        print(f"\n🔑 Key Usage Details:")
        for key_info in key_details:
            print(f"   {key_info['name']}: {key_info['total_requests']} requests, status: {key_info['status']}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())