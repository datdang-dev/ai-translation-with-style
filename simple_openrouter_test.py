#!/usr/bin/env python3
"""
Simple OpenRouter test - giống implementation cũ
Chỉ gửi request với preset config, không có complex architecture
"""

import asyncio
import aiohttp
import json

async def simple_openrouter_test(api_key: str):
    """Test OpenRouter đơn giản như implementation cũ"""
    
    # Preset config đơn giản
    preset_config = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": [
            {
                "role": "user", 
                "content": "Translate this to Vietnamese: Hello, how are you today?"
            }
        ],
        "max_tokens": 100,
        "temperature": 0.3
    }
    
    # Headers đơn giản
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print("🚀 Simple OpenRouter Test (giống implementation cũ)")
    print(f"📡 Model: {preset_config['model']}")
    print(f"🔑 API Key: {api_key[:8]}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=preset_config,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                print(f"📊 Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    print(f"✅ Success!")
                    print(f"   Response: {content}")
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    # Đọc API key từ config
    try:
        with open("config/api_keys.json", "r") as f:
            config = json.load(f)
            api_key = config["api_keys"]["openrouter"]
            
        print(f"✅ API key loaded: {api_key[:8]}...")
        
        # Test OpenRouter
        asyncio.run(simple_openrouter_test(api_key))
        
    except Exception as e:
        print(f"❌ Failed to load API key: {e}")
        print("Hãy đặt API key vào config/api_keys.json")
        exit(1)
