#!/usr/bin/env python3
"""
Check API keys file structure
"""

import json
import os

def check_api_keys_file():
    """Check the structure of api_keys.json file"""
    print("🔍 CHECKING API KEYS FILE STRUCTURE...")
    
    api_keys_path = "config/api_keys.json"
    
    if not os.path.exists(api_keys_path):
        print(f"❌ API keys file not found: {api_keys_path}")
        return
    
    try:
        with open(api_keys_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("📄 API Keys File Content:")
        print(content)
        print("\n" + "="*50)
        
        # Parse JSON
        data = json.loads(content)
        print(f"📋 Parsed JSON type: {type(data)}")
        print(f"📋 Parsed JSON value: {data}")
        
        if isinstance(data, dict):
            print(f"✅ Root is dict with keys: {list(data.keys())}")
            
            if 'api_keys' in data:
                api_keys = data['api_keys']
                print(f"📋 api_keys type: {type(api_keys)}")
                print(f"📋 api_keys value: {api_keys}")
                
                if isinstance(api_keys, dict):
                    print(f"✅ api_keys is dict with keys: {list(api_keys.keys())}")
                elif isinstance(api_keys, list):
                    print(f"🚨 PROBLEM: api_keys is LIST! Should be dict!")
                    print(f"    List content: {api_keys}")
                else:
                    print(f"⚠️ api_keys is unexpected type: {type(api_keys)}")
            else:
                print("❌ No 'api_keys' key found in JSON")
        elif isinstance(data, list):
            print(f"🚨 PROBLEM: Root JSON is LIST! Should be dict!")
            print(f"    List content: {data}")
        else:
            print(f"⚠️ Root JSON is unexpected type: {type(data)}")
        
    except Exception as e:
        print(f"❌ Failed to read/parse API keys file: {e}")
        import traceback
        traceback.print_exc()

def show_correct_format():
    """Show correct API keys file format"""
    print("\n🔧 CORRECT API KEYS FILE FORMAT:")
    print("File: config/api_keys.json")
    print("Content should be:")
    
    correct_format = {
        "api_keys": {
            "openrouter": "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",
            "google_translate": None
        }
    }
    
    print(json.dumps(correct_format, indent=2))

if __name__ == "__main__":
    check_api_keys_file()
    show_correct_format()