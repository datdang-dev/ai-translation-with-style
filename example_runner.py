#!/usr/bin/env python3
"""
Example runner for the AI Translation Framework

This script demonstrates how to use the new refactored architecture
with both real and fake OpenRouter API calls.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.models import (
    TranslationRequest, BatchTranslationRequest, ProviderConfig, 
    ProviderType, ModelConfig, ProvidersConfig, SourceLanguage, TargetLanguage, TranslationStyle
)
from src.core.services import ProviderRegistry, TranslationService
from src.infrastructure.providers import create_openrouter_provider
from src.infrastructure.config import setup_logging, LoggingSettings, LogLevel, LogFormat
from src.infrastructure.observability import get_logger, setup_metrics
from pydantic import SecretStr


async def setup_framework():
    """Setup the translation framework"""
    
    # Setup logging
    logging_settings = LoggingSettings(
        level=LogLevel.INFO,
        format=LogFormat.COLORED,
        enable_file_logging=False,
        enable_console_logging=True
    )
    setup_logging(logging_settings)
    
    # Setup metrics
    setup_metrics(enable_prometheus=False)
    
    logger = get_logger("example_runner")
    logger.info("🚀 Setting up AI Translation Framework")
    
    return logger


async def create_test_provider_config(use_fake: bool = True) -> ProviderConfig:
    """Create a test provider configuration"""
    
    # Create model configurations
    models = [
        ModelConfig(
            name="anthropic/claude-3.5-sonnet",
            display_name="Claude 3.5 Sonnet",
            max_input_tokens=200000,
            max_output_tokens=4096,
            supports_streaming=True,
            input_cost_per_1k_tokens=0.003,
            output_cost_per_1k_tokens=0.015,
            default_temperature=0.3,
            quality_tier="premium"
        ),
        ModelConfig(
            name="anthropic/claude-3-haiku",
            display_name="Claude 3 Haiku", 
            max_input_tokens=200000,
            max_output_tokens=4096,
            supports_streaming=True,
            input_cost_per_1k_tokens=0.00025,
            output_cost_per_1k_tokens=0.00125,
            default_temperature=0.3,
            quality_tier="standard"
        )
    ]
    
    # API keys (empty for fake provider)
    api_keys = []
    if not use_fake:
        # Check for real API key in environment
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            api_keys = [SecretStr(openrouter_key)]
    
    config = ProviderConfig(
        name="openrouter",
        type=ProviderType.OPENROUTER,
        display_name="OpenRouter",
        description="OpenRouter API for multiple AI models",
        base_url="https://openrouter.ai/api/v1",
        timeout_seconds=30,
        api_keys=api_keys,
        models=models,
        default_model="anthropic/claude-3.5-sonnet",
        enabled=True,
        priority=1
    )
    
    return config


async def run_single_translation_example(service: TranslationService, logger):
    """Run single translation example"""
    logger.info("=" * 60)
    logger.info("🔤 Single Translation Example")
    logger.info("=" * 60)
    
    # Create translation request
    request = TranslationRequest(
        text="Hello, how are you doing today? I hope you're having a great day!",
        source_language=SourceLanguage.ENGLISH,
        target_language=TargetLanguage.VIETNAMESE,
        style=TranslationStyle.CONVERSATIONAL,
        context="Casual greeting between friends"
    )
    
    logger.info(f"📝 Original text: {request.text}")
    logger.info(f"🌍 {request.source_language} → {request.target_language}")
    logger.info(f"🎨 Style: {request.style}")
    
    # Perform translation
    result = await service.translate_single(request)
    
    # Display results
    if result.is_success:
        logger.info(f"✅ Translation successful!")
        logger.info(f"📄 Translated text: {result.translated_text}")
        logger.info(f"⏱️  Processing time: {result.total_processing_time_ms}ms")
        
        if result.metrics:
            logger.info(f"🏭 Provider: {result.metrics.provider_name}")
            logger.info(f"🤖 Model: {result.metrics.model_name}")
            logger.info(f"📊 Confidence: {result.metrics.confidence_score}")
    else:
        logger.error(f"❌ Translation failed!")
        logger.error(f"🚨 Error: {result.error.message}")
        logger.error(f"🔄 Retryable: {result.error.is_retryable}")


async def run_batch_translation_example(service: TranslationService, logger):
    """Run batch translation example"""
    logger.info("=" * 60)
    logger.info("📦 Batch Translation Example")
    logger.info("=" * 60)
    
    # Create multiple translation requests
    texts = [
        "Good morning! How can I help you?",
        "Thank you for your patience.",
        "Please wait a moment while I process your request.",
        "Have a wonderful day!",
        "See you later!"
    ]
    
    requests = []
    for i, text in enumerate(texts):
        request = TranslationRequest(
            text=text,
            source_language=SourceLanguage.ENGLISH,
            target_language=TargetLanguage.VIETNAMESE,
            style=TranslationStyle.FORMAL,
            context="Customer service interactions"
        )
        requests.append(request)
    
    # Create batch request
    batch_request = BatchTranslationRequest(
        requests=requests,
        max_concurrent=3,
        shared_style=TranslationStyle.FORMAL
    )
    
    logger.info(f"📦 Batch size: {len(batch_request.requests)}")
    logger.info(f"🔄 Max concurrent: {batch_request.max_concurrent}")
    logger.info(f"🎨 Shared style: {batch_request.shared_style}")
    
    # Perform batch translation
    batch_result = await service.translate_batch(batch_request)
    
    # Display results
    logger.info(f"📊 Batch Results:")
    logger.info(f"   ✅ Successful: {batch_result.successful_requests}")
    logger.info(f"   ❌ Failed: {batch_result.failed_requests}")
    logger.info(f"   📈 Success rate: {batch_result.success_rate:.1f}%")
    logger.info(f"   ⏱️  Total time: {batch_result.total_processing_time_ms}ms")
    
    # Show individual results
    logger.info("🔍 Individual Results:")
    for i, result in enumerate(batch_result.results):
        if result.is_success:
            logger.info(f"   {i+1}. ✅ {texts[i]} → {result.translated_text}")
        else:
            logger.info(f"   {i+1}. ❌ {texts[i]} → ERROR: {result.error.message}")


async def run_provider_health_example(service: TranslationService, logger):
    """Run provider health check example"""
    logger.info("=" * 60)
    logger.info("🏥 Provider Health Check Example")
    logger.info("=" * 60)
    
    # Get service stats
    stats = await service.get_service_stats()
    
    logger.info("🏭 Provider Information:")
    for name, info in stats["providers"].items():
        status = "✅ Healthy" if stats["health_status"].get(name, False) else "❌ Unhealthy"
        logger.info(f"   {name}: {status}")
        logger.info(f"      Type: {info['type']}")
        logger.info(f"      Models: {len(info['models'])}")
        logger.info(f"      Default Model: {info['default_model']}")
        logger.info(f"      Priority: {info['priority']}")
    
    logger.info(f"⚙️  Service Configuration:")
    logger.info(f"   Max Concurrent: {stats['max_concurrent_requests']}")
    logger.info(f"   Fallback Enabled: {stats['enable_fallback']}")
    logger.info(f"   Active Requests: {stats['active_requests']}")


async def run_cost_estimation_example(service: TranslationService, logger):
    """Run cost estimation example"""
    logger.info("=" * 60)
    logger.info("💰 Cost Estimation Example")
    logger.info("=" * 60)
    
    # Create a longer text for cost estimation
    long_text = """
    Artificial Intelligence (AI) has revolutionized numerous industries and continues to shape the future of technology. 
    From machine learning algorithms that power recommendation systems to natural language processing models that enable 
    seamless communication between humans and computers, AI has become an integral part of our daily lives. 
    
    The development of large language models has particularly transformed how we interact with information and automate 
    complex tasks. These models can understand context, generate human-like text, and even translate between languages 
    with remarkable accuracy. As we continue to advance in this field, the potential applications seem limitless.
    
    However, with great power comes great responsibility. The ethical implications of AI development, including concerns 
    about bias, privacy, and job displacement, must be carefully considered as we move forward. It's crucial that we 
    develop AI systems that are not only powerful but also fair, transparent, and beneficial to society as a whole.
    """
    
    request = TranslationRequest(
        text=long_text.strip(),
        source_language=SourceLanguage.ENGLISH,
        target_language=TargetLanguage.VIETNAMESE,
        style=TranslationStyle.TECHNICAL,
        model_name="anthropic/claude-3.5-sonnet"
    )
    
    logger.info(f"📝 Text length: {len(request.text)} characters")
    logger.info(f"🤖 Model: {request.model_name}")
    
    # Get provider and estimate cost
    try:
        provider = await service.provider_registry.get_provider("openrouter")
        estimated_cost = await provider.estimate_cost(request)
        
        if estimated_cost:
            logger.info(f"💵 Estimated cost: ${estimated_cost:.6f} USD")
        else:
            logger.info("💵 Cost estimation not available")
    except Exception as e:
        logger.error(f"❌ Cost estimation failed: {e}")


async def main():
    """Main example runner"""
    logger = await setup_framework()
    
    try:
        # Check for real API key
        use_fake = not bool(os.getenv("OPENROUTER_API_KEY"))
        
        if use_fake:
            logger.info("🎭 Using FAKE provider (no API key found)")
            logger.info("💡 Set OPENROUTER_API_KEY environment variable to use real API")
        else:
            logger.info("🔑 Using REAL OpenRouter API")
        
        # Create provider configuration
        provider_config = await create_test_provider_config(use_fake=use_fake)
        
        # Create provider registry
        providers_config = ProvidersConfig(
            providers=[provider_config],
            default_provider="openrouter",
            enable_fallback=True
        )
        
        registry = ProviderRegistry(providers_config)
        
        # Register OpenRouter provider factory
        registry.register_provider_factory(
            "openrouter", 
            lambda config: create_openrouter_provider(config, use_fake=use_fake)
        )
        
        # Initialize providers
        await registry.initialize_providers()
        
        # Create translation service
        service = TranslationService(
            provider_registry=registry,
            max_concurrent_requests=5,
            enable_fallback=True
        )
        
        logger.info("✅ Framework setup complete!")
        
        # Run examples
        await run_single_translation_example(service, logger)
        await run_batch_translation_example(service, logger)
        await run_provider_health_example(service, logger)
        await run_cost_estimation_example(service, logger)
        
        logger.info("=" * 60)
        logger.info("🎉 All examples completed successfully!")
        logger.info("=" * 60)
        
        # Cleanup
        await service.close()
        
    except Exception as e:
        logger.error(f"❌ Example runner failed: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)