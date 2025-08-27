#!/usr/bin/env python3
"""
Debug test để tìm nguyên nhân lỗi 'list' object has no attribute 'get'
"""

import sys
sys.path.append('.')

def test_config_loading():
    """Test loading configuration từ YAML"""
    print("🧪 Testing configuration loading...")
    
    try:
        from services.config.configuration_manager import ConfigurationManager
        
        config_manager = ConfigurationManager('config/translation.yaml')
        print("✅ ConfigurationManager created successfully")
        
        # Test provider configs
        provider_configs = config_manager.get_provider_configs()
        print(f"📋 Provider configs type: {type(provider_configs)}")
        print(f"📋 Provider configs keys: {list(provider_configs.keys())}")
        
        for name, config in provider_configs.items():
            print(f"\n🔍 Provider '{name}':")
            print(f"  - Type: {type(config)}")
            print(f"  - Enabled: {config.enabled}")
            print(f"  - Config type: {type(config.config)}")
            print(f"  - Config value: {config.config}")
            
            # Check if config.config is dict or list
            if isinstance(config.config, dict):
                print(f"  - Config keys: {list(config.config.keys())}")
            elif isinstance(config.config, list):
                print(f"  - Config list length: {len(config.config)}")
                print(f"  - Config list items: {config.config}")
            else:
                print(f"  - Config unexpected type: {type(config.config)}")
        
        return True, provider_configs
        
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_service_factory():
    """Test ServiceFactory provider creation"""
    print("\n🧪 Testing ServiceFactory...")
    
    try:
        from services.config.service_factory import ServiceFactory
        from services.config.configuration_manager import ConfigurationManager
        
        config_manager = ConfigurationManager('config/translation.yaml')
        factory = ServiceFactory(config_manager)
        
        print("✅ ServiceFactory created successfully")
        
        # Test individual provider creation
        provider_configs = config_manager.get_provider_configs()
        api_keys = config_manager.get_api_keys()
        
        print(f"📋 API Keys: {api_keys}")
        
        for name, config in provider_configs.items():
            print(f"\n🔍 Testing provider '{name}' creation:")
            print(f"  - Config type: {type(config)}")
            print(f"  - Config.config type: {type(config.config)}")
            
            try:
                provider = factory._create_provider(name, config, api_keys)
                if provider:
                    print(f"  ✅ Provider created successfully: {type(provider)}")
                else:
                    print(f"  ⚠️ Provider creation returned None")
            except Exception as e:
                print(f"  ❌ Provider creation failed: {e}")
                import traceback
                traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ ServiceFactory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_yaml_structure():
    """Test direct YAML loading"""
    print("\n🧪 Testing direct YAML loading...")
    
    try:
        import yaml
        
        with open('config/translation.yaml', 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
        
        print("✅ YAML loaded successfully")
        print(f"📋 YAML keys: {list(yaml_data.keys())}")
        
        if 'providers' in yaml_data:
            providers = yaml_data['providers']
            print(f"📋 Providers type: {type(providers)}")
            print(f"📋 Providers keys: {list(providers.keys())}")
            
            for name, provider_data in providers.items():
                print(f"\n🔍 Provider '{name}' in YAML:")
                print(f"  - Type: {type(provider_data)}")
                print(f"  - Keys: {list(provider_data.keys()) if isinstance(provider_data, dict) else 'Not a dict'}")
                
                if 'config' in provider_data:
                    config_data = provider_data['config']
                    print(f"  - Config type: {type(config_data)}")
                    print(f"  - Config value: {config_data}")
        
        return True, yaml_data
        
    except Exception as e:
        print(f"❌ YAML test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def main():
    """Run all debug tests"""
    print("🚀 Starting debug tests...\n")
    
    # Test 1: Direct YAML loading
    yaml_success, yaml_data = test_yaml_structure()
    
    # Test 2: Configuration loading
    config_success, provider_configs = test_config_loading()
    
    # Test 3: ServiceFactory
    factory_success = test_service_factory()
    
    print("\n" + "="*50)
    print("📊 DEBUG SUMMARY:")
    print(f"  - YAML loading: {'✅' if yaml_success else '❌'}")
    print(f"  - Config loading: {'✅' if config_success else '❌'}")
    print(f"  - ServiceFactory: {'✅' if factory_success else '❌'}")
    
    if not all([yaml_success, config_success, factory_success]):
        print("\n❌ Found issues - check logs above for details")
        return 1
    else:
        print("\n✅ All tests passed!")
        return 0

if __name__ == "__main__":
    exit(main())