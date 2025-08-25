#!/usr/bin/env python3
"""
Simplified example runner for the AI Translation Framework

This demonstrates the core architecture without external dependencies.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


# Simplified models (without Pydantic for this demo)
class TranslationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SimpleTranslationRequest:
    text: str
    source_language: str = "auto"
    target_language: str = "vi"
    style: str = "conversational"
    request_id: str = field(default_factory=lambda: f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}")


@dataclass
class SimpleTranslationResult:
    request_id: str
    status: TranslationStatus
    original_text: str
    target_language: str
    translated_text: Optional[str] = None
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    provider_name: str = "unknown"
    
    @property
    def is_success(self) -> bool:
        return self.status == TranslationStatus.COMPLETED and self.translated_text is not None


# Simplified provider interface
class SimpleTranslationProvider:
    def __init__(self, name: str, provider_type: str):
        self.name = name
        self.provider_type = provider_type
    
    async def translate(self, request: SimpleTranslationRequest) -> SimpleTranslationResult:
        raise NotImplementedError


# Fake OpenRouter provider
class FakeOpenRouterProvider(SimpleTranslationProvider):
    def __init__(self):
        super().__init__("openrouter", "openrouter")
        print(f"🎭 Initialized {self.name} provider (FAKE MODE)")
    
    async def translate(self, request: SimpleTranslationRequest) -> SimpleTranslationResult:
        print(f"🔄 Translating: {request.text[:50]}...")
        
        # Simulate API delay
        await asyncio.sleep(0.5)
        
        # Create fake translation based on target language
        fake_translations = {
            "vi": f"[TIẾNG VIỆT GIẢ] {request.text}",
            "en": f"[FAKE ENGLISH] {request.text}",
            "ja": f"[偽の日本語] {request.text}",
            "ko": f"[가짜 한국어] {request.text}",
            "zh-CN": f"[假中文] {request.text}",
            "es": f"[ESPAÑOL FALSO] {request.text}",
            "fr": f"[FAUX FRANÇAIS] {request.text}",
        }
        
        translated_text = fake_translations.get(
            request.target_language,
            f"[FAKE {request.target_language.upper()}] {request.text}"
        )
        
        result = SimpleTranslationResult(
            request_id=request.request_id,
            status=TranslationStatus.COMPLETED,
            original_text=request.text,
            target_language=request.target_language,
            translated_text=translated_text,
            processing_time_ms=500,
            provider_name=self.name
        )
        
        print(f"✅ Translation completed: {translated_text[:50]}...")
        return result
    
    async def health_check(self) -> bool:
        return True


# Simple provider registry
class SimpleProviderRegistry:
    def __init__(self):
        self.providers: Dict[str, SimpleTranslationProvider] = {}
    
    def register_provider(self, provider: SimpleTranslationProvider):
        self.providers[provider.name] = provider
        print(f"📝 Registered provider: {provider.name}")
    
    async def get_provider(self, name: str) -> SimpleTranslationProvider:
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' not found")
        return self.providers[name]
    
    async def get_default_provider(self) -> SimpleTranslationProvider:
        if not self.providers:
            raise ValueError("No providers available")
        return list(self.providers.values())[0]


# Simple translation service
class SimpleTranslationService:
    def __init__(self, registry: SimpleProviderRegistry):
        self.registry = registry
    
    async def translate_single(
        self, 
        request: SimpleTranslationRequest,
        provider_name: Optional[str] = None
    ) -> SimpleTranslationResult:
        try:
            if provider_name:
                provider = await self.registry.get_provider(provider_name)
            else:
                provider = await self.registry.get_default_provider()
            
            return await provider.translate(request)
        except Exception as e:
            return SimpleTranslationResult(
                request_id=request.request_id,
                status=TranslationStatus.FAILED,
                original_text=request.text,
                target_language=request.target_language,
                error_message=str(e)
            )
    
    async def translate_batch(self, requests: List[SimpleTranslationRequest]) -> List[SimpleTranslationResult]:
        tasks = [self.translate_single(req) for req in requests]
        return await asyncio.gather(*tasks)


async def run_single_translation_demo():
    """Demo single translation"""
    print("=" * 60)
    print("🔤 Single Translation Demo")
    print("=" * 60)
    
    # Create request
    request = SimpleTranslationRequest(
        text="Hello, how are you doing today? I hope you're having a great day!",
        source_language="en",
        target_language="vi",
        style="conversational"
    )
    
    print(f"📝 Original: {request.text}")
    print(f"🌍 {request.source_language} → {request.target_language}")
    
    # Setup service
    registry = SimpleProviderRegistry()
    registry.register_provider(FakeOpenRouterProvider())
    service = SimpleTranslationService(registry)
    
    # Translate
    result = await service.translate_single(request)
    
    # Show results
    if result.is_success:
        print(f"✅ Success!")
        print(f"📄 Translation: {result.translated_text}")
        print(f"⏱️  Time: {result.processing_time_ms}ms")
        print(f"🏭 Provider: {result.provider_name}")
    else:
        print(f"❌ Failed: {result.error_message}")


async def run_batch_translation_demo():
    """Demo batch translation"""
    print("=" * 60)
    print("📦 Batch Translation Demo")
    print("=" * 60)
    
    # Create requests
    texts = [
        "Good morning!",
        "How can I help you?",
        "Thank you for waiting.",
        "Have a nice day!",
        "See you soon!"
    ]
    
    requests = [
        SimpleTranslationRequest(text=text, target_language="vi")
        for text in texts
    ]
    
    print(f"📦 Batch size: {len(requests)}")
    
    # Setup service
    registry = SimpleProviderRegistry()
    registry.register_provider(FakeOpenRouterProvider())
    service = SimpleTranslationService(registry)
    
    # Translate batch
    results = await service.translate_batch(requests)
    
    # Show results
    successful = sum(1 for r in results if r.is_success)
    print(f"📊 Results: {successful}/{len(results)} successful")
    
    for i, result in enumerate(results):
        if result.is_success:
            print(f"   {i+1}. ✅ {texts[i]} → {result.translated_text}")
        else:
            print(f"   {i+1}. ❌ {texts[i]} → ERROR")


async def run_architecture_demo():
    """Demo the architecture components"""
    print("=" * 60)
    print("🏗️  Architecture Demo")
    print("=" * 60)
    
    # Show the architecture in action
    print("🔧 Components:")
    print("   1. SimpleTranslationRequest - Request model")
    print("   2. SimpleTranslationResult - Result model")
    print("   3. FakeOpenRouterProvider - Provider implementation")
    print("   4. SimpleProviderRegistry - Provider management")
    print("   5. SimpleTranslationService - Core orchestration")
    
    print("\n🎯 Key Features Demonstrated:")
    print("   ✅ Clean separation of concerns")
    print("   ✅ Async/await throughout")
    print("   ✅ Provider abstraction")
    print("   ✅ Error handling")
    print("   ✅ Batch processing")
    print("   ✅ Fake responses for testing")
    
    print("\n🚀 This is the foundation for:")
    print("   - Real API integration")
    print("   - Multiple provider support")
    print("   - Rate limiting & retry logic")
    print("   - Observability & metrics")
    print("   - Configuration management")


async def main():
    """Main demo runner"""
    print("🚀 AI Translation Framework - Simplified Demo")
    print("🎭 Running with FAKE responses (no API keys needed)")
    print()
    
    try:
        await run_single_translation_demo()
        await run_batch_translation_demo()
        await run_architecture_demo()
        
        print("=" * 60)
        print("🎉 Demo completed successfully!")
        print("💡 This demonstrates the new refactored architecture")
        print("🔑 Set OPENROUTER_API_KEY to use real API in full version")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)