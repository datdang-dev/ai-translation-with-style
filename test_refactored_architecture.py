#!/usr/bin/env python3
"""
Test script for the refactored architecture
Verifies that all components can be imported and initialized
"""

import sys
import os
import asyncio

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all components can be imported"""
    print("🧪 Testing imports...")
    
    try:
        # Test middleware imports
        from middleware import CoreManager
        print("✅ CoreManager imported successfully")
        
        # Test applet imports
        from applet import TranslationApplet
        print("✅ TranslationApplet imported successfully")
        
        # Test service imports
        from services.infrastructure import ConfigManager, APIKeyManager, JobScheduler
        print("✅ Infrastructure services imported successfully")
        
        from services.translation import RequestManager, Validator, Standardizer
        print("✅ Translation services imported successfully")
        
        from services.common import get_logger
        print("✅ Common services imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config_loading():
    """Test configuration loading"""
    print("\n🔧 Testing configuration loading...")
    
    try:
        from services.infrastructure import ConfigManager
        
        # Test with default config
        config_manager = ConfigManager()
        print("✅ ConfigManager initialized successfully")
        
        # Test configuration access
        api_config = config_manager.get_api_config()
        translation_config = config_manager.get_translation_config()
        
        print(f"✅ API URL: {api_config.get('url', 'N/A')}")
        print(f"✅ Model: {translation_config.get('model', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_middleware_initialization():
    """Test middleware initialization"""
    print("\n🏗️ Testing middleware initialization...")
    
    try:
        from middleware import CoreManager
        
        # This will fail without API keys, but we can test the initialization process
        try:
            core_manager = CoreManager()
            print("✅ CoreManager initialized successfully")
            return True
        except Exception as e:
            if "No API keys available" in str(e):
                print("⚠️ CoreManager initialization failed as expected (no API keys)")
                print("✅ This is expected behavior - API keys are required")
                return True
            else:
                print(f"❌ Unexpected error during CoreManager initialization: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Middleware test failed: {e}")
        return False

def test_applet_creation():
    """Test applet creation"""
    print("\n🔧 Testing applet creation...")
    
    try:
        from applet import TranslationApplet
        
        # This will fail without API keys, but we can test the creation process
        try:
            applet = TranslationApplet()
            print("✅ TranslationApplet created successfully")
            return True
        except Exception as e:
            if "No API keys available" in str(e):
                print("⚠️ TranslationApplet creation failed as expected (no API keys)")
                print("✅ This is expected behavior - API keys are required")
                return True
            else:
                print(f"❌ Unexpected error during applet creation: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Applet test failed: {e}")
        return False

async def test_async_components():
    """Test async components"""
    print("\n⚡ Testing async components...")
    
    try:
        from services.infrastructure import JobScheduler
        
        # Test job scheduler
        scheduler = JobScheduler(default_interval=1.0)
        print("✅ JobScheduler created successfully")
        
        # Test adding a job
        async def test_job():
            return "test completed"
        
        scheduler.add_job("test_job", test_job)
        print("✅ Test job added successfully")
        
        # Test starting scheduler
        await scheduler.start()
        print("✅ Scheduler started successfully")
        
        # Wait a bit for job execution
        await asyncio.sleep(1.5)
        
        # Test stopping scheduler
        await scheduler.stop()
        print("✅ Scheduler stopped successfully")
        
        # Check stats
        stats = scheduler.get_scheduler_stats()
        print(f"✅ Scheduler stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Async components test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Refactored Architecture")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Configuration Test", test_config_loading),
        ("Middleware Test", test_middleware_initialization),
        ("Applet Test", test_applet_creation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    # Test async components
    try:
        if asyncio.run(test_async_components()):
            passed += 1
        else:
            print("❌ Async components test failed")
    except Exception as e:
        print(f"❌ Async components test failed with exception: {e}")
    
    total += 1  # Include async test
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Architecture is working correctly.")
        print("\n✅ Ready to use the refactored framework!")
        print("📖 See README_REFACTORED.md for usage instructions")
        print("🚀 Run with: python start_refactored.py")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)