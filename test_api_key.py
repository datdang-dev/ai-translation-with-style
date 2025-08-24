#!/usr/bin/env python3
"""
Test API key directly
"""

import asyncio
import aiohttp
import json

#   "api_keys": [
#     "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",
#     "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",
#     "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"
#   ]
# }

async def test_api_key():
    """Test API key directly with OpenRouter"""
    
    api_key = "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"
    api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    # Simple test payload
    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {"role": "user", "content": "Hello, say 'test successful' in Vietnamese"}
        ],
        "max_tokens": 50
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print("🧪 Testing API Key...")
    print(f"🔑 Key: {api_key[:20]}...")
    print(f"🌐 URL: {api_url}")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                print(f"📊 Status Code: {response.status}")
                print(f"📋 Response Headers: {dict(response.headers)}")
                
                response_text = await response.text()
                print(f"📄 Response Body: {response_text[:500]}...")
                
                if response.status == 200:
                    print("✅ API Key is working!")
                    try:
                        result = json.loads(response_text)
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        print(f"🤖 AI Response: {content}")
                    except:
                        print("⚠️  Could not parse JSON response")
                elif response.status == 401:
                    print("❌ API Key is invalid or expired!")
                    print("💡 Please check your API key at: https://openrouter.ai/keys")
                elif response.status == 429:
                    print("⚠️  Rate limit exceeded!")
                else:
                    print(f"❌ Unexpected error: {response.status}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_api_key())
