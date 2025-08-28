"""
Refactored translation orchestrator using the new architecture.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional

from services.core.interfaces import *
from services.core.dependency_container import DIContainer
from services.core.configuration_service import ConfigurationService
from services.key_management.enhanced_key_manager import EnhancedAPIKeyManager
from services.api_clients.base_client import MockAPIClient
from services.monitoring.metrics_service import MetricsService, TimedOperation
from services.resilience.circuit_breaker import CircuitBreakerManager
from services.common.logger import get_logger


class RefactoredTranslationOrchestrator:
    """Refactored translation orchestrator with improved architecture"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.logger = get_logger("RefactoredOrchestrator")
        self._setup_services()
    
    def _setup_services(self) -> None:
        """Setup services using dependency injection"""
        # Create DI container
        self.container = DIContainer()
        
        # Register configuration service
        config_service = ConfigurationService(self.config_path)
        self.container.register_singleton(IConfigurationService, config_service)
        
        # Register metrics service
        metrics_service = MetricsService()
        self.container.register_singleton(IMetricsService, metrics_service)
        
        # Register enhanced key manager
        key_manager = EnhancedAPIKeyManager(config_service)
        self.container.register_singleton(IAPIKeyManager, key_manager)
        
        # Register circuit breaker manager
        circuit_breaker_manager = CircuitBreakerManager(config_service)
        self.container.register_singleton(CircuitBreakerManager, circuit_breaker_manager)
        
        # Register API client (using mock for demo)
        api_client = MockAPIClient(
            key_manager, metrics_service, self.logger, 
            simulate_errors=True, error_rate=0.1
        )
        self.container.register_singleton(IAPIClient, api_client)
        
        # Store references for easy access
        self.config_service = config_service
        self.metrics_service = metrics_service
        self.key_manager = key_manager
        self.circuit_breaker_manager = circuit_breaker_manager
        self.api_client = api_client
    
    async def translate_text(self, text: str) -> Result:
        """Translate text using the refactored architecture"""
        
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
            
            self.logger.info(f"Translating text: {text[:100]}...")
            
            # Use circuit breaker for API call
            result = await self.circuit_breaker_manager.call_with_breaker(
                "api_client",
                self.api_client.send_request,
                request_data
            )
            
            if result.success:
                self.metrics_service.increment_counter("translation.success")
                self.logger.info("Translation completed successfully")
                
                # Extract translated text from response
                try:
                    response_data = result.data
                    translated_text = response_data["choices"][0]["message"]["content"]
                    return Result.ok({"translated_text": translated_text, "original_text": text})
                except (KeyError, IndexError) as e:
                    self.logger.error(f"Failed to extract translation from response: {e}")
                    return Result.error(500, "Invalid response format")
            else:
                self.metrics_service.increment_counter("translation.error")
                self.logger.error(f"Translation failed: {result.error_message}")
                return result
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        
        # Get key manager stats
        key_stats = await self.key_manager.get_manager_stats()
        
        # Get circuit breaker stats
        circuit_stats = await self.circuit_breaker_manager.get_all_statuses()
        
        # Get metrics summary
        metrics_summary = self.metrics_service.get_summary()
        
        return {
            "timestamp": time.time(),
            "status": "healthy",
            "key_management": key_stats,
            "circuit_breakers": circuit_stats,
            "metrics": metrics_summary,
            "configuration": {
                "client_type": self.config_service.get("client_type"),
                "max_concurrent": self.config_service.get("batch.max_concurrent"),
                "total_api_keys": len(self.config_service.get_api_keys())
            }
        }
    
    async def demonstrate_resilience(self) -> None:
        """Demonstrate the resilience features"""
        self.logger.info("=== Demonstrating Resilience Features ===")
        
        # Test multiple translations
        test_texts = [
            "Hello world!",
            "How are you today?",
            "This is a test translation.",
            "The weather is nice today.",
            "Thank you for your help.",
        ]
        
        results = []
        for i, text in enumerate(test_texts):
            self.logger.info(f"Test {i+1}: Translating '{text}'")
            result = await self.translate_text(text)
            results.append(result)
            
            if result.success:
                self.logger.info(f"✅ Success: {result.data['translated_text']}")
            else:
                self.logger.error(f"❌ Failed: {result.error_message}")
            
            # Small delay between requests
            await asyncio.sleep(0.5)
        
        # Print system status
        status = await self.get_system_status()
        self.logger.info("=== System Status ===")
        self.logger.info(f"Key Management: {status['key_management']['summary']}")
        self.logger.info(f"Metrics: {status['metrics']}")
        
        return results


async def main():
    """Demo the refactored architecture"""
    print("🚀 Refactored Translation Service Demo")
    print("=" * 50)
    
    # Initialize orchestrator
    orchestrator = RefactoredTranslationOrchestrator("config/refactored_demo.json")
    
    try:
        # Single translation test
        print("\n📝 Single Translation Test")
        result = await orchestrator.translate_text("Hello, this is a test message!")
        if result.success:
            print(f"✅ Translation: {result.data['translated_text']}")
        else:
            print(f"❌ Error: {result.error_message}")
        
        # Resilience demonstration
        print("\n🛡️  Resilience Demonstration")
        await orchestrator.demonstrate_resilience()
        
        # System status
        print("\n📊 Final System Status")
        status = await orchestrator.get_system_status()
        print(f"Total API Keys: {status['configuration']['total_api_keys']}")
        print(f"Active Keys: {status['key_management']['summary']['active_keys']}")
        print(f"Total Metrics: {status['metrics']['total_counters']} counters, {status['metrics']['total_histograms']} histograms")
        
        # Show detailed metrics
        print("\n📈 Detailed Metrics")
        metrics = orchestrator.metrics_service.get_metrics()
        for counter_name, counter_data in metrics['counters'].items():
            print(f"  {counter_name}: {counter_data['value']}")
        
        for histogram_name, histogram_data in metrics['histograms'].items():
            stats = histogram_data['stats']
            if stats:
                print(f"  {histogram_name}: count={stats['count']}, mean={stats['mean']:.3f}s")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())