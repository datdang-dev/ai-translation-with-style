#!/usr/bin/env python3
"""
Debug script để chạy trực tiếp trong project của user
"""

import sys
import os
import traceback

def debug_config_structure():
    """Debug configuration structure in detail"""
    print("🔍 DEBUGGING CONFIG STRUCTURE...")
    
    try:
        from services.config.configuration_manager import ConfigurationManager
        
        # Load config
        config_manager = ConfigurationManager('config/translation.yaml')
        print("✅ ConfigurationManager loaded")
        
        # Get provider configs
        provider_configs = config_manager.get_provider_configs()
        print(f"📋 Provider configs type: {type(provider_configs)}")
        
        for name, config in provider_configs.items():
            print(f"\n🔍 DETAILED DEBUG for '{name}':")
            print(f"  - Config object type: {type(config)}")
            print(f"  - Config object: {config}")
            print(f"  - Config.enabled: {config.enabled}")
            print(f"  - Config.config type: {type(config.config)}")
            print(f"  - Config.config value: {repr(config.config)}")
            
            # Check if it's a list
            if isinstance(config.config, list):
                print(f"  🚨 CONFIG.CONFIG IS A LIST!")
                print(f"     List length: {len(config.config)}")
                print(f"     List contents: {config.config}")
                for i, item in enumerate(config.config):
                    print(f"     Item {i}: {type(item)} = {item}")
            elif isinstance(config.config, dict):
                print(f"  ✅ Config.config is dict with keys: {list(config.config.keys())}")
            else:
                print(f"  ⚠️ Config.config is unexpected type: {type(config.config)}")
        
        return provider_configs
        
    except Exception as e:
        print(f"❌ Config debug failed: {e}")
        traceback.print_exc()
        return None

def debug_yaml_loading():
    """Debug YAML loading directly"""
    print("\n🔍 DEBUGGING YAML LOADING...")
    
    try:
        import yaml
        
        with open('config/translation.yaml', 'r', encoding='utf-8') as f:
            yaml_content = f.read()
        
        print("📄 YAML File Content (first 500 chars):")
        print(yaml_content[:500])
        print("...")
        
        # Load YAML
        yaml_data = yaml.safe_load(yaml_content)
        print(f"\n📋 YAML loaded successfully")
        print(f"Top-level keys: {list(yaml_data.keys())}")
        
        if 'providers' in yaml_data:
            providers = yaml_data['providers']
            print(f"\n📋 Providers in YAML:")
            for name, provider_data in providers.items():
                print(f"  {name}:")
                print(f"    Type: {type(provider_data)}")
                print(f"    Keys: {list(provider_data.keys()) if isinstance(provider_data, dict) else 'Not dict'}")
                if 'config' in provider_data:
                    config_data = provider_data['config']
                    print(f"    Config type: {type(config_data)}")
                    print(f"    Config value: {repr(config_data)}")
        
        return yaml_data
        
    except Exception as e:
        print(f"❌ YAML debug failed: {e}")
        traceback.print_exc()
        return None

def debug_service_factory_creation():
    """Debug service factory provider creation step by step"""
    print("\n🔍 DEBUGGING SERVICE FACTORY...")
    
    try:
        from services.config.configuration_manager import ConfigurationManager
        from services.config.service_factory import ServiceFactory
        
        config_manager = ConfigurationManager('config/translation.yaml')
        factory = ServiceFactory(config_manager)
        
        # Get configs
        provider_configs = config_manager.get_provider_configs()
        api_keys = config_manager.get_api_keys()
        
        print(f"📋 API Keys: {api_keys}")
        
        # Test each provider creation manually
        for name, config in provider_configs.items():
            print(f"\n🔧 MANUAL PROVIDER CREATION TEST: '{name}'")
            print(f"  Config type: {type(config)}")
            print(f"  Config.config type: {type(config.config)}")
            print(f"  Config.config value: {repr(config.config)}")
            
            # Step-by-step recreation of _create_provider logic
            if name == 'openrouter':
                api_key = api_keys.get('openrouter') or api_keys.get('openrouter_api_key')
                print(f"  API key found: {api_key is not None}")
                
                if api_key:
                    # The problematic line
                    print(f"  Testing config.config access...")
                    print(f"  config.config type: {type(config.config)}")
                    
                    if isinstance(config.config, dict):
                        preset_name = config.config.get('preset', 'preset_translation')
                        print(f"  ✅ Got preset name: {preset_name}")
                    elif isinstance(config.config, list):
                        print(f"  🚨 config.config is LIST - this is the problem!")
                        print(f"     List content: {config.config}")
                    else:
                        print(f"  ⚠️ config.config is {type(config.config)}")
            
            # Try actual creation
            try:
                provider = factory._create_provider(name, config, api_keys)
                print(f"  ✅ Provider created: {provider is not None}")
            except Exception as e:
                print(f"  ❌ Provider creation failed: {e}")
                print(f"     Error type: {type(e)}")
                traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Service factory debug failed: {e}")
        traceback.print_exc()

def main():
    print("🚀 STARTING DETAILED DEBUG IN PROJECT...")
    print(f"📂 Current directory: {os.getcwd()}")
    print(f"🐍 Python path: {sys.path[:3]}")
    
    # Debug steps
    yaml_data = debug_yaml_loading()
    provider_configs = debug_config_structure()
    debug_service_factory_creation()
    
    print("\n" + "="*60)
    print("🎯 SUMMARY:")
    print("Look for '🚨' markers above to find the exact issue!")
    print("="*60)

if __name__ == "__main__":
    main()