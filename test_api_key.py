#!/usr/bin/env python3
"""
Test API key directly
"""

import asyncio
import aiohttp
import json
import requests
#   "api_keys": [
#     "sk-or-v1-xx1",
#     "sk-or-v1-xx2",
#     "sk-or-v1-xx3"
#   ]
# }

async def test_api_key():
    """Test API key directly with OpenRouter"""
    
    api_key = "sk-or-v1-xx4"
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
    print("\n")
    response = requests.get(
    url="https://openrouter.ai/api/v1/key",
    headers={
        "Authorization": f"Bearer {api_key}"
    }
    )
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(test_api_key())
