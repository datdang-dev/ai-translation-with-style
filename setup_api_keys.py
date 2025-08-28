#!/usr/bin/env python3
"""
Setup script for configuring API keys.
"""

import json
import os
import sys
from pathlib import Path


def main():
    print("🔑 API Key Setup for Translation Service")
    print("=" * 50)
    
    # Check if template exists
    template_path = "config/api_keys.json.template"
    if not os.path.exists(template_path):
        print(f"❌ Template file not found: {template_path}")
        return
    
    # Target path for API keys
    api_keys_path = "config/api_keys.json"
    
    # Check if file already exists
    if os.path.exists(api_keys_path):
        response = input(f"⚠️  {api_keys_path} already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            return
    
    print(f"\n📋 Instructions:")
    print("1. Get your API keys from: https://openrouter.ai/keys")
    print("2. You can add multiple keys for better rate limiting")
    print("3. Keys should start with 'sk-or-v1-'")
    print()
    
    # Collect API keys
    api_keys = []
    
    while True:
        if not api_keys:
            prompt = "Enter your first OpenRouter API key: "
        else:
            prompt = f"Enter another API key (or press Enter to finish): "
        
        key = input(prompt).strip()
        
        if not key:
            if api_keys:
                break
            else:
                print("❌ You must enter at least one API key!")
                continue
        
        # Basic validation
        if not key.startswith("sk-or-v1-"):
            print("⚠️  Warning: API key should start with 'sk-or-v1-'")
            response = input("Use this key anyway? (y/N): ")
            if response.lower() != 'y':
                continue
        
        api_keys.append(key)
        print(f"✅ Added key {len(api_keys)}")
    
    # Create the configuration
    config = {
        "api_keys": api_keys
    }
    
    # Save to file
    try:
        with open(api_keys_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✅ Successfully saved {len(api_keys)} API key(s) to {api_keys_path}")
        print(f"🔒 Keep this file secure and don't commit it to version control!")
        
        # Add to .gitignore if it exists
        gitignore_path = ".gitignore"
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                content = f.read()
            
            if "config/api_keys.json" not in content:
                with open(gitignore_path, 'a') as f:
                    f.write("\n# API keys\nconfig/api_keys.json\n")
                print(f"✅ Added api_keys.json to .gitignore")
        
        print(f"\n🚀 Next steps:")
        print(f"1. Install aiohttp: pip install aiohttp")
        print(f"2. Run production demo: python3 production_orchestrator.py")
        print(f"3. Or run batch processing: python3 batch_production.py")
        
    except Exception as e:
        print(f"❌ Failed to save configuration: {e}")


if __name__ == "__main__":
    main()