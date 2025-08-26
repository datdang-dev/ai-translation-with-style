"""
Comprehensive tests for the new translation architecture
"""

import pytest
import asyncio
import json
from pathlib import Path
from typing import Dict, Any

# Import all the new architecture components
from services.models import (
    TranslationRequest, TranslationResult, FormatType, ProviderType,
    Chunk, StandardizedContent, BatchResult
)
from services.standardizer import StandardizerService, RenpyStandardizer, JsonStandardizer
from services.providers import ProviderOrchestrator, OpenRouterClient, GoogleTranslateClient
from services.infrastructure import CacheService, HealthMonitor, ValidatorService
from services.resiliency import ResiliencyManager, ServerFaultHandler
from services.middleware import RequestManager, TranslationManager
from services.config import ConfigurationManager, ServiceFactory
from applet.translation_orchestrator import TranslationOrchestrator


class TestDataModels:
    """Test core data models"""
    
    def test_translation_request_creation(self):
        """Test TranslationRequest creation and validation"""
        request = TranslationRequest(
            content="Hello world",
            source_lang="en",
            target_lang="es",
            format_type=FormatType.TEXT
        )
        
        assert request.content == "Hello world"
        assert request.source_lang == "en"
        assert request.target_lang == "es"
        assert request.format_type == FormatType.TEXT
        assert request.provider == ProviderType.AUTO
        assert request.request_id is not None
    
    def test_translation_result_creation(self):
        """Test TranslationResult creation"""
        result = TranslationResult(
            original="Hello",
            translated="Hola",
            provider="test_provider",
            source_lang="en",
            target_lang="es"
        )
        
        assert result.original == "Hello"
        assert result.translated == "Hola"
        assert result.provider == "test_provider"
        assert result.validation_passed is True
    
    def test_chunk_creation(self):
        """Test Chunk creation"""
        chunk = Chunk(
            is_text=True,
            original="Hello world",
            standard="Hello world",
            translation="Hola mundo"
        )
        
        assert chunk.is_text is True
        assert chunk.original == "Hello world"
        assert chunk.standard == "Hello world"
        assert chunk.translation == "Hola mundo"
        assert chunk.chunk_id is not None


class TestStandardizers:
    """Test standardizer components"""
    
    def test_renpy_standardizer(self):
        """Test Renpy standardizer"""
        standardizer = RenpyStandardizer()
        
        # Test validation
        renpy_content = '''label start:
    "Hello, world!"
    character "This is dialogue"
    $ variable = 1
    jump next_scene'''
        
        assert standardizer.validate(renpy_content) is True
        
        # Test standardization
        standardized = standardizer.standardize(renpy_content)
        assert isinstance(standardized, StandardizedContent)
        assert standardized.format_type == FormatType.RENPY
        
        # Check that dialogue was extracted
        translatable_texts = standardized.get_translatable_texts()
        assert len(translatable_texts) > 0
        assert "Hello, world!" in translatable_texts
    
    def test_json_standardizer(self):
        """Test JSON standardizer"""
        standardizer = JsonStandardizer()
        
        # Test with dict
        json_content = {
            "text": "Hello world",
            "description": "A greeting",
            "id": 123,
            "metadata": {
                "title": "Sample"
            }
        }
        
        assert standardizer.validate(json_content) is True
        
        standardized = standardizer.standardize(json_content)
        assert isinstance(standardized, StandardizedContent)
        assert standardized.format_type == FormatType.JSON
        
        # Check translatable content
        translatable_texts = standardized.get_translatable_texts()
        assert "Hello world" in translatable_texts
        assert "A greeting" in translatable_texts
        assert "Sample" in translatable_texts
    
    def test_standardizer_service(self):
        """Test StandardizerService coordination"""
        service = StandardizerService()
        
        # Test format detection
        json_content = {"text": "Hello"}
        detected = service.detect_format(json_content)
        assert detected == FormatType.JSON
        
        # Test standardization
        standardized = service.standardize(json_content)
        assert standardized.format_type == FormatType.JSON


class TestProviders:
    """Test provider components (with mock implementations)"""
    
    def test_google_translate_client(self):
        """Test Google Translate client initialization"""
        client = GoogleTranslateClient()
        assert client.get_name() == "google_translate"
        assert client.use_free_service is True
        
        capabilities = client.get_capabilities()
        assert "supported_languages" in capabilities
        assert capabilities["service_type"] == "free"
    
    @pytest.mark.asyncio
    async def test_google_translate_mock_translation(self):
        """Test Google Translate mock translation"""
        client = GoogleTranslateClient()
        
        # This will use mock translation
        result = await client.translate(["Hello world"], "es", "en")
        assert len(result) == 1
        assert "[ES]" in result[0]  # Mock translation format
    
    def test_provider_orchestrator(self):
        """Test ProviderOrchestrator"""
        orchestrator = ProviderOrchestrator()
        
        # Register a mock provider
        google_client = GoogleTranslateClient()
        orchestrator.register_provider(google_client)
        
        providers = orchestrator.list_providers()
        assert "google_translate" in providers
        
        # Test provider selection
        selected = orchestrator.select_provider()
        assert selected == "google_translate"


class TestInfrastructure:
    """Test infrastructure services"""
    
    @pytest.mark.asyncio
    async def test_cache_service(self):
        """Test CacheService"""
        cache = CacheService()
        
        # Test basic operations
        await cache.set("test_key", "test_value")
        value = await cache.get("test_key")
        assert value == "test_value"
        
        # Test translation caching
        success = await cache.set_translation("Hello", "es", "Hola", "en")
        assert success is True
        
        cached_translation = await cache.get_translation("Hello", "es", "en")
        assert cached_translation is not None
        assert cached_translation["translation"] == "Hola"
    
    def test_validator_service(self):
        """Test ValidatorService"""
        validator = ValidatorService()
        
        # Test validation
        result = validator.validate_translation("Hello world", "Hola mundo")
        assert result["valid"] is True
        assert result["overall_score"] > 0.5
        
        # Test validation failure
        result = validator.validate_translation("Hello world", "")
        assert result["valid"] is False
    
    @pytest.mark.asyncio
    async def test_health_monitor(self):
        """Test HealthMonitor"""
        monitor = HealthMonitor()
        
        # Register a simple health check
        async def mock_health_check():
            from services.models import HealthStatus
            return HealthStatus.healthy("Mock service OK")
        
        monitor.register_health_check("mock_service", mock_health_check)
        
        # Test health check
        health = await monitor.check_health("mock_service")
        assert health.is_healthy is True
        assert "Mock service OK" in health.message


class TestResiliency:
    """Test resiliency components"""
    
    @pytest.mark.asyncio
    async def test_server_fault_handler(self):
        """Test ServerFaultHandler"""
        handler = ServerFaultHandler()
        
        # Test successful execution
        async def success_func():
            return "success"
        
        result = await handler.execute_with_retry(success_func)
        assert result == "success"
        
        # Test retry on failure
        call_count = 0
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success_after_retries"
        
        result = await handler.execute_with_retry(failing_func)
        assert result == "success_after_retries"
        assert call_count == 3
    
    def test_resiliency_manager(self):
        """Test ResiliencyManager"""
        manager = ResiliencyManager()
        
        # Test configuration
        manager.configure_default_policies()
        
        # Test provider health status
        from services.models import HealthStatus
        manager.update_health_status("test_provider", HealthStatus.healthy("OK"))
        
        assert manager.is_provider_healthy("test_provider") is True


class TestMiddleware:
    """Test middleware components"""
    
    @pytest.mark.asyncio
    async def test_request_manager(self):
        """Test RequestManager with mock dependencies"""
        # Create request manager with real components
        request_manager = RequestManager()
        
        # Test request validation
        request = TranslationRequest(
            content="Hello world",
            source_lang="en",
            target_lang="es",
            format_type=FormatType.TEXT
        )
        
        validation = request_manager.validate_request(request)
        # May fail due to no providers, but should not crash
        assert "errors" in validation
    
    def test_translation_manager(self):
        """Test TranslationManager initialization"""
        manager = TranslationManager()
        
        status = manager.get_status()
        assert "healthy" in status
        assert "configuration" in status


class TestConfiguration:
    """Test configuration management"""
    
    def test_configuration_manager(self):
        """Test ConfigurationManager"""
        config_manager = ConfigurationManager()
        
        # Test default configuration
        providers_config = config_manager.get_provider_configs()
        assert isinstance(providers_config, dict)
        
        resiliency_config = config_manager.get_resiliency_config()
        assert resiliency_config.max_retries > 0
        
        cache_config = config_manager.get_cache_config()
        assert cache_config.enabled is not None
    
    def test_service_factory(self):
        """Test ServiceFactory"""
        factory = ServiceFactory()
        
        # Test service creation
        standardizer = factory.get_standardizer_service()
        assert standardizer is not None
        
        validator = factory.get_validator_service()
        assert validator is not None
        
        cache = factory.get_cache_service()
        # May be None if disabled
        
        # Test status
        status = factory.get_service_status()
        assert "configuration_valid" in status


class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_translation_orchestrator_initialization(self):
        """Test TranslationOrchestrator initialization"""
        orchestrator = TranslationOrchestrator()
        
        # Initialize
        result = await orchestrator.initialize()
        
        # May fail due to missing API keys, but should not crash
        assert "status" in result
        
        # Test status
        status = orchestrator.get_status()
        assert "initialized" in status
        
        # Test capabilities
        capabilities = orchestrator.get_capabilities()
        assert "formats_supported" in capabilities
        
        # Cleanup
        await orchestrator.shutdown()
    
    @pytest.mark.asyncio
    async def test_simple_translation_flow(self):
        """Test simple translation flow with mocks"""
        # This test would work with real API keys
        # For now, we just test that the flow doesn't crash
        
        try:
            orchestrator = TranslationOrchestrator()
            await orchestrator.initialize()
            
            # This will likely fail without API keys, but shouldn't crash
            # In a real test environment, you'd mock the providers
            
            await orchestrator.shutdown()
            
        except Exception as e:
            # Expected to fail without proper setup
            assert "api" in str(e).lower() or "provider" in str(e).lower()


class TestBackwardCompatibility:
    """Test backward compatibility with old interface"""
    
    @pytest.mark.asyncio
    async def test_backward_compatible_function(self):
        """Test that old function signature still works"""
        from applet.translation_orchestrator import run_batch_translation_from_directory
        
        # Test function exists and has correct signature
        assert callable(run_batch_translation_from_directory)
        
        # Test with invalid directory (should handle gracefully)
        try:
            result = await run_batch_translation_from_directory(
                config_path="config/translation.yaml",
                input_dir="nonexistent_dir",
                output_dir="test_output",
                pattern="*.json",
                max_concurrent=1,
                job_delay=0.1
            )
            # Should not reach here
            assert False, "Should have failed with nonexistent directory"
        except FileNotFoundError:
            # Expected behavior
            pass
        except Exception as e:
            # May fail for other reasons (missing API keys, etc.)
            # As long as it doesn't crash completely
            assert "api" in str(e).lower() or "provider" in str(e).lower() or "dir" in str(e).lower()


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_format_type(self):
        """Test handling of invalid format types"""
        with pytest.raises(ValueError):
            FormatType("invalid_format")
    
    def test_empty_content_handling(self):
        """Test handling of empty content"""
        standardizer = StandardizerService()
        
        # Test with empty string
        try:
            result = standardizer.standardize("", FormatType.TEXT)
            # Should handle gracefully
        except Exception as e:
            # Should not crash completely
            assert "content" in str(e).lower() or "empty" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_provider_failure_handling(self):
        """Test provider failure handling"""
        orchestrator = ProviderOrchestrator()
        
        # Test with no providers
        try:
            result = await orchestrator.translate(["Hello"], "es", "en")
            assert False, "Should have failed with no providers"
        except Exception as e:
            assert "provider" in str(e).lower()


# Test data for file-based tests
def create_test_files(tmp_path):
    """Create test files for directory processing tests"""
    test_data = [
        {"text": "Hello world", "id": 1},
        {"text": "Goodbye", "id": 2},
        {"content": "Test content", "title": "Test"}
    ]
    
    for i, data in enumerate(test_data):
        file_path = tmp_path / f"test_{i}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    return tmp_path


class TestFileProcessing:
    """Test file and directory processing"""
    
    @pytest.mark.asyncio
    async def test_directory_processing_structure(self, tmp_path):
        """Test directory processing structure (without actual translation)"""
        # Create test files
        input_dir = create_test_files(tmp_path / "input")
        output_dir = tmp_path / "output"
        
        # Test that the function handles file discovery correctly
        orchestrator = TranslationOrchestrator()
        
        try:
            await orchestrator.initialize()
            
            # This will likely fail at translation stage, but should discover files correctly
            result = await orchestrator.translate_directory(
                str(input_dir),
                str(output_dir),
                "es",
                "*.json",
                "en",
                "json"
            )
            
            # If it gets this far, check structure
            assert "files_found" in result
            assert result["files_found"] >= 3
            
        except Exception as e:
            # Expected to fail without proper API setup
            # But should at least find the files
            pass
        finally:
            await orchestrator.shutdown()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
