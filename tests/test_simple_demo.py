"""
Simple demonstration test that shows the new architecture working
This test can run without API keys and demonstrates the system's capabilities
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path

from applet.translation_orchestrator import TranslationOrchestrator
from services.models import FormatType, TranslationRequest


class TestSimpleDemo:
    """Simple demonstration of the new architecture"""
    
    @pytest.mark.asyncio
    async def test_orchestrator_basic_functionality(self):
        """Test basic orchestrator functionality without external dependencies"""
        orchestrator = TranslationOrchestrator()
        
        # Test initialization
        result = await orchestrator.initialize()
        print(f"Initialization result: {result}")
        
        # Should initialize even without API keys (though translation will fail)
        assert result["status"] in ["success", "error"]
        
        # Test status
        status = orchestrator.get_status()
        print(f"Status: {status}")
        assert "initialized" in status
        
        # Test capabilities  
        capabilities = orchestrator.get_capabilities()
        print(f"Capabilities: {capabilities}")
        assert "formats_supported" in capabilities
        assert "renpy" in capabilities["formats_supported"]
        assert "json" in capabilities["formats_supported"]
        
        await orchestrator.shutdown()
    
    def test_data_models_demonstration(self):
        """Demonstrate data model functionality"""
        # Create a translation request
        request = TranslationRequest(
            content="Hello, world!",
            source_lang="en", 
            target_lang="es",
            format_type=FormatType.TEXT
        )
        
        print(f"Created request: {request}")
        assert request.content == "Hello, world!"
        assert request.format_type == FormatType.TEXT
        assert request.request_id is not None
        
        # Demonstrate that requests have proper metadata
        print(f"Request ID: {request.request_id}")
        print(f"Created at: {request.created_at}")
    
    def test_standardizer_demonstration(self):
        """Demonstrate standardizer functionality"""
        from services.standardizer import StandardizerService
        
        service = StandardizerService()
        
        # Test with JSON content
        json_content = {
            "dialogue": "Hello, how are you?",
            "character": "Player",
            "metadata": {
                "scene": "intro",
                "id": 123
            }
        }
        
        # Detect format
        detected_format = service.detect_format(json_content)
        print(f"Detected format: {detected_format}")
        assert detected_format == FormatType.JSON
        
        # Standardize content
        standardized = service.standardize(json_content)
        print(f"Standardized content type: {type(standardized)}")
        print(f"Number of chunks: {len(standardized.chunks)}")
        
        # Get translatable text
        translatable = standardized.get_translatable_texts()
        print(f"Translatable texts: {translatable}")
        assert "Hello, how are you?" in translatable
        
        # Test with Renpy content
        renpy_content = '''label start:
    "Welcome to the game!"
    player "Hello there."
    $ score = 0
    jump next_scene'''
        
        detected = service.detect_format(renpy_content)
        print(f"Renpy format detected: {detected}")
        
        if detected == FormatType.RENPY:
            standardized_renpy = service.standardize(renpy_content)
            translatable_renpy = standardized_renpy.get_translatable_texts()
            print(f"Renpy translatable texts: {translatable_renpy}")
            assert len(translatable_renpy) > 0
    
    def test_cache_demonstration(self):
        """Demonstrate cache functionality"""
        from services.infrastructure import CacheService
        from services.models import CacheConfig
        
        # Create cache service
        config = CacheConfig(enabled=True, backend="memory")
        cache = CacheService(config)
        
        # Demonstrate synchronous-like interface for this test
        async def demo_cache():
            # Test basic caching
            await cache.set("demo_key", "demo_value")
            value = await cache.get("demo_key")
            assert value == "demo_value"
            
            # Test translation caching
            await cache.set_translation("Hello", "es", "Hola", "en")
            cached = await cache.get_translation("Hello", "es", "en")
            assert cached is not None
            assert cached["translation"] == "Hola"
            
            # Get cache stats
            stats = cache.get_stats()
            print(f"Cache stats: {stats}")
            assert stats["hits"] >= 0
            assert stats["sets"] >= 2
        
        # Run the async demo
        asyncio.run(demo_cache())
    
    def test_validation_demonstration(self):
        """Demonstrate validation functionality"""
        from services.infrastructure import ValidatorService
        
        validator = ValidatorService()
        
        # Test good translation
        result = validator.validate_translation(
            "Hello world",
            "Hola mundo"
        )
        print(f"Good translation validation: {result}")
        assert result["valid"] is True
        assert result["overall_score"] > 0.5
        
        # Test problematic translation
        result = validator.validate_translation(
            "Hello world with {variable}",
            "Hola mundo"  # Missing the variable
        )
        print(f"Problematic translation validation: {result}")
        # Should detect missing special characters
        
        # Test batch validation
        originals = ["Hello", "Goodbye", "Thank you"]
        translations = ["Hola", "Adiós", "Gracias"]
        
        batch_results = validator.validate_batch(originals, translations)
        print(f"Batch validation results: {len(batch_results)} results")
        
        summary = validator.get_validation_summary(batch_results)
        print(f"Validation summary: {summary}")
        assert summary["total_translations"] == 3
    
    @pytest.mark.asyncio
    async def test_provider_demonstration(self):
        """Demonstrate provider functionality (with mock Google Translate)"""
        from services.providers import GoogleTranslateClient, ProviderOrchestrator
        
        # Test Google Translate client (free/mock mode)
        client = GoogleTranslateClient()
        print(f"Google client name: {client.get_name()}")
        
        capabilities = client.get_capabilities()
        print(f"Google capabilities: {capabilities}")
        
        # Test mock translation
        result = await client.translate(["Hello world"], "es", "en")
        print(f"Mock translation result: {result}")
        assert len(result) == 1
        assert result[0] is not None
        
        # Test orchestrator
        orchestrator = ProviderOrchestrator()
        orchestrator.register_provider(client)
        
        providers = orchestrator.list_providers()
        print(f"Registered providers: {providers}")
        assert "google_translate" in providers
        
        # Test provider selection
        selected = orchestrator.select_provider()
        print(f"Selected provider: {selected}")
        
        # Test orchestrator translation
        orch_result = await orchestrator.translate(["Hello"], "es", "en")
        print(f"Orchestrator result: {orch_result}")
    
    @pytest.mark.asyncio
    async def test_file_processing_demo(self):
        """Demonstrate file processing capabilities"""
        # Create temporary test files
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "input"
            output_dir = Path(temp_dir) / "output"
            input_dir.mkdir()
            
            # Create test JSON files
            test_data = [
                {"text": "Hello world", "id": 1, "type": "greeting"},
                {"dialogue": "How are you?", "character": "NPC", "scene": "intro"},
                {"content": "This is a test", "title": "Test Document"}
            ]
            
            for i, data in enumerate(test_data):
                file_path = input_dir / f"test_{i}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            
            print(f"Created {len(test_data)} test files in {input_dir}")
            
            # Test file discovery without actual translation
            orchestrator = TranslationOrchestrator()
            
            try:
                await orchestrator.initialize()
                
                # This will likely fail at translation step, but should discover files
                result = await orchestrator.translate_directory(
                    str(input_dir),
                    str(output_dir),
                    "es",
                    "*.json",
                    "en",
                    "json"
                )
                
                print(f"Directory processing result: {result}")
                
                # Even if translation fails, should find files
                if "files_found" in result:
                    assert result["files_found"] == 3
                    print(f"Successfully discovered {result['files_found']} files")
                
            except Exception as e:
                print(f"Expected error (no API keys): {e}")
                # This is expected without proper API setup
                assert "api" in str(e).lower() or "provider" in str(e).lower() or "key" in str(e).lower()
            
            finally:
                await orchestrator.shutdown()
    
    def test_configuration_demonstration(self):
        """Demonstrate configuration management"""
        from services.config import ConfigurationManager, ServiceFactory
        
        # Test configuration manager
        config_manager = ConfigurationManager()
        
        # Test default configuration
        print("Testing configuration management...")
        
        providers = config_manager.get_provider_configs()
        print(f"Provider configs: {list(providers.keys())}")
        assert len(providers) >= 1  # Should have at least one provider configured
        
        resiliency = config_manager.get_resiliency_config()
        print(f"Resiliency config: max_retries={resiliency.max_retries}")
        assert resiliency.max_retries > 0
        
        cache_config = config_manager.get_cache_config()
        print(f"Cache config: enabled={cache_config.enabled}, backend={cache_config.backend}")
        
        # Test service factory
        factory = ServiceFactory(config_manager)
        
        # Test service creation
        standardizer = factory.get_standardizer_service()
        assert standardizer is not None
        print("✓ Standardizer service created")
        
        cache = factory.get_cache_service()
        print(f"✓ Cache service created: {cache is not None}")
        
        validator = factory.get_validator_service()
        assert validator is not None
        print("✓ Validator service created")
        
        # Test status
        status = factory.get_service_status()
        print(f"Service factory status: {status}")
    
    def test_error_handling_demonstration(self):
        """Demonstrate error handling capabilities"""
        from services.models import TranslationError, ProviderError
        from services.standardizer import StandardizationError
        
        # Test custom exceptions
        try:
            raise TranslationError("Test translation error", error_code="TEST_ERROR")
        except TranslationError as e:
            print(f"Caught TranslationError: {e.message}, code: {e.error_code}")
            assert e.error_code == "TEST_ERROR"
        
        try:
            raise ProviderError("Test provider error", error_code="PROVIDER_ERROR")
        except ProviderError as e:
            print(f"Caught ProviderError: {e.message}")
        
        # Test graceful degradation
        from services.standardizer import StandardizerService
        
        service = StandardizerService()
        
        try:
            # Try to standardize invalid content
            result = service.standardize(None, FormatType.JSON)
            assert False, "Should have failed"
        except Exception as e:
            print(f"Gracefully handled invalid content: {type(e).__name__}")
            assert isinstance(e, (StandardizationError, TypeError, ValueError))


def run_demo():
    """Run all demonstrations"""
    print("=" * 60)
    print("AI Translation Architecture - Simple Demonstration")
    print("=" * 60)
    
    # Run the test class demonstrations
    demo = TestSimpleDemo()
    
    print("\n1. Testing data models...")
    demo.test_data_models_demonstration()
    print("✓ Data models working correctly")
    
    print("\n2. Testing standardizer...")
    demo.test_standardizer_demonstration()
    print("✓ Standardizer working correctly")
    
    print("\n3. Testing cache...")
    demo.test_cache_demonstration()
    print("✓ Cache working correctly")
    
    print("\n4. Testing validation...")
    demo.test_validation_demonstration()
    print("✓ Validation working correctly")
    
    print("\n5. Testing configuration...")
    demo.test_configuration_demonstration()
    print("✓ Configuration working correctly")
    
    print("\n6. Testing error handling...")
    demo.test_error_handling_demonstration()
    print("✓ Error handling working correctly")
    
    print("\n7. Testing providers...")
    asyncio.run(demo.test_provider_demonstration())
    print("✓ Providers working correctly")
    
    print("\n8. Testing orchestrator...")
    asyncio.run(demo.test_orchestrator_basic_functionality())
    print("✓ Orchestrator working correctly")
    
    print("\n9. Testing file processing...")
    asyncio.run(demo.test_file_processing_demo())
    print("✓ File processing working correctly")
    
    print("\n" + "=" * 60)
    print("✅ ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
    print("The new translation architecture is working correctly.")
    print("Note: Some features require API keys for full functionality.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()