#!/usr/bin/env python3
"""
Simple test script for the refactored architecture
Tests basic structure without external dependencies
"""

import sys
import os

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_file_structure():
    """Test that all required files exist"""
    print("📁 Testing file structure...")
    
    required_files = [
        "middleware/__init__.py",
        "middleware/core_manager.py",
        "applet/__init__.py",
        "applet/translation_applet.py",
        "services/__init__.py",
        "services/common/__init__.py",
        "services/infrastructure/__init__.py",
        "services/translation/__init__.py",
        "config/config.yaml",
        "config/prompts.json",
        "start_refactored.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files exist")
        return True

def test_config_files():
    """Test configuration files"""
    print("\n⚙️ Testing configuration files...")
    
    try:
        # Test YAML config
        import yaml
        with open("config/config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        
        required_keys = ['api', 'translation', 'scheduling', 'validation', 'standardization']
        missing_keys = [key for key in required_keys if key not in config]
        
        if missing_keys:
            print(f"❌ Missing config keys: {missing_keys}")
            return False
        
        print("✅ YAML configuration is valid")
        
        # Test JSON prompts
        import json
        with open("config/prompts.json", 'r') as f:
            prompts = json.load(f)
        
        required_prompts = ['system_message', 'format_rules', 'style_rules', 'translation_flow']
        missing_prompts = [prompt for prompt in required_prompts if prompt not in prompts]
        
        if missing_prompts:
            print(f"❌ Missing prompts: {missing_prompts}")
            return False
        
        print("✅ JSON prompts are valid")
        return True
        
    except ImportError:
        print("⚠️ PyYAML not available, skipping config validation")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_python_syntax():
    """Test that Python files have valid syntax"""
    print("\n🐍 Testing Python syntax...")
    
    python_files = [
        "middleware/core_manager.py",
        "applet/translation_applet.py",
        "services/infrastructure/config_manager.py",
        "services/infrastructure/key_manager.py",
        "services/infrastructure/job_scheduler.py",
        "services/translation/validator.py",
        "services/translation/standardizer.py",
        "services/translation/request_manager.py"
    ]
    
    failed_files = []
    for file_path in python_files:
        try:
            with open(file_path, 'r') as f:
                compile(f.read(), file_path, 'exec')
            print(f"✅ {file_path} - Valid syntax")
        except SyntaxError as e:
            print(f"❌ {file_path} - Syntax error: {e}")
            failed_files.append(file_path)
        except Exception as e:
            print(f"❌ {file_path} - Error: {e}")
            failed_files.append(file_path)
    
    if failed_files:
        print(f"❌ {len(failed_files)} files have syntax errors")
        return False
    else:
        print("✅ All Python files have valid syntax")
        return True

def test_import_structure():
    """Test basic import structure without external dependencies"""
    print("\n📦 Testing import structure...")
    
    try:
        # Test that we can read the files and they have the right structure
        with open("middleware/__init__.py", 'r') as f:
            content = f.read()
            if "CoreManager" in content:
                print("✅ Middleware init exports CoreManager")
            else:
                print("❌ Middleware init missing CoreManager export")
                return False
        
        with open("applet/__init__.py", 'r') as f:
            content = f.read()
            if "TranslationApplet" in content:
                print("✅ Applet init exports TranslationApplet")
            else:
                print("❌ Applet init missing TranslationApplet export")
                return False
        
        with open("services/infrastructure/__init__.py", 'r') as f:
            content = f.read()
            if "ConfigManager" in content and "APIKeyManager" in content:
                print("✅ Infrastructure services init exports required classes")
            else:
                print("❌ Infrastructure services init missing required exports")
                return False
        
        with open("services/translation/__init__.py", 'r') as f:
            content = f.read()
            if "RequestManager" in content and "Validator" in content:
                print("✅ Translation services init exports required classes")
            else:
                print("❌ Translation services init missing required exports")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Import structure test failed: {e}")
        return False

def test_architecture_design():
    """Test that the architecture follows the design principles"""
    print("\n🏗️ Testing architecture design...")
    
    design_checks = [
        ("Single Applet Component", "applet/translation_applet.py exists and is the only applet"),
        ("Middleware CoreManager", "middleware/core_manager.py exists as single entry point"),
        ("Service Grouping", "services are grouped into infrastructure, translation, and common"),
        ("Configuration Separation", "config.yaml for settings, prompts.json for AI instructions"),
        ("Timer-based Scheduling", "job_scheduler.py implements timer-based execution"),
        ("Strategy Pattern", "validator.py uses strategy pattern for validation"),
        ("Interface Pattern", "standardizer.py uses interface pattern for input conversion")
    ]
    
    all_passed = True
    for check_name, description in design_checks:
        try:
            if check_name == "Single Applet Component":
                # Check that only one applet file exists
                applet_files = [f for f in os.listdir("applet") if f.endswith(".py") and f != "__init__.py"]
                if len(applet_files) == 1 and applet_files[0] == "translation_applet.py":
                    print(f"✅ {check_name}: {description}")
                else:
                    print(f"❌ {check_name}: Expected single applet, found {applet_files}")
                    all_passed = False
            
            elif check_name == "Middleware CoreManager":
                # Check that CoreManager exists and is the main export
                if os.path.exists("middleware/core_manager.py"):
                    with open("middleware/__init__.py", 'r') as f:
                        content = f.read()
                        if "CoreManager" in content:
                            print(f"✅ {check_name}: {description}")
                        else:
                            print(f"❌ {check_name}: CoreManager not exported")
                            all_passed = False
                else:
                    print(f"❌ {check_name}: core_manager.py not found")
                    all_passed = False
            
            elif check_name == "Service Grouping":
                # Check service directory structure
                if (os.path.exists("services/infrastructure") and 
                    os.path.exists("services/translation") and 
                    os.path.exists("services/common")):
                    print(f"✅ {check_name}: {description}")
                else:
                    print(f"❌ {check_name}: Service directories not properly grouped")
                    all_passed = False
            
            elif check_name == "Configuration Separation":
                # Check config file separation
                if (os.path.exists("config/config.yaml") and 
                    os.path.exists("config/prompts.json")):
                    print(f"✅ {check_name}: {description}")
                else:
                    print(f"❌ {check_name}: Configuration files not properly separated")
                    all_passed = False
            
            elif check_name == "Timer-based Scheduling":
                # Check job scheduler implementation
                with open("services/infrastructure/job_scheduler.py", 'r') as f:
                    content = f.read()
                    if "default_interval" in content and "next_run" in content:
                        print(f"✅ {check_name}: {description}")
                    else:
                        print(f"❌ {check_name}: Timer-based scheduling not implemented")
                        all_passed = False
            
            elif check_name == "Strategy Pattern":
                # Check validator strategy pattern
                with open("services/translation/validator.py", 'r') as f:
                    content = f.read()
                    if "ValidationStrategy" in content and "set_strategy" in content:
                        print(f"✅ {check_name}: {description}")
                    else:
                        print(f"❌ {check_name}: Strategy pattern not implemented")
                        all_passed = False
            
            elif check_name == "Interface Pattern":
                # Check standardizer interface pattern
                with open("services/translation/standardizer.py", 'r') as f:
                    content = f.read()
                    if "StandardizationInterface" in content and "ABC" in content:
                        print(f"✅ {check_name}: {description}")
                    else:
                        print(f"❌ {check_name}: Interface pattern not implemented")
                        all_passed = False
        
        except Exception as e:
            print(f"❌ {check_name}: Test failed with error: {e}")
            all_passed = False
    
    return all_passed

def main():
    """Run all tests"""
    print("🚀 Testing Refactored Architecture Structure")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Configuration Files", test_config_files),
        ("Python Syntax", test_python_syntax),
        ("Import Structure", test_import_structure),
        ("Architecture Design", test_architecture_design),
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
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Architecture structure is correct.")
        print("\n✅ The refactored framework is properly structured!")
        print("📖 See README_REFACTORED.md for detailed documentation")
        print("🚀 To run with dependencies: pip install -r requirements.txt")
        print("🚀 Then run: python start_refactored.py")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)