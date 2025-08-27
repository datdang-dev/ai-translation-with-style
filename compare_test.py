#!/usr/bin/env python3
"""
Test để so sánh code giữa workspace và project thực
"""

import sys
import hashlib
import os

def get_file_hash(filepath):
    """Get file hash for comparison"""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

def compare_files():
    """Compare key files between workspace and target"""
    
    target_base = "/home/datdang/working/ai-translation-with-style"
    workspace_base = "/workspace"
    
    files_to_compare = [
        "services/config/service_factory.py",
        "services/config/configuration_manager.py", 
        "services/config/preset_loader.py",
        "services/config/__init__.py",
        "services/providers/openrouter_client.py",
        "config/translation.yaml",
        "config/preset_translation.json",
        "run_batch.py"
    ]
    
    print("🔍 Comparing files between workspace and target...")
    print(f"Workspace: {workspace_base}")
    print(f"Target: {target_base}")
    print("="*60)
    
    differences_found = False
    
    for file_path in files_to_compare:
        workspace_file = os.path.join(workspace_base, file_path)
        target_file = os.path.join(target_base, file_path)
        
        workspace_hash = get_file_hash(workspace_file)
        target_hash = get_file_hash(target_file)
        
        workspace_exists = os.path.exists(workspace_file)
        target_exists = os.path.exists(target_file)
        
        status = "✅"
        if workspace_hash != target_hash:
            status = "❌"
            differences_found = True
        elif not target_exists:
            status = "🚫" 
            differences_found = True
        elif not workspace_exists:
            status = "⚠️"
            differences_found = True
            
        print(f"{status} {file_path}")
        print(f"    Workspace: {'EXISTS' if workspace_exists else 'MISSING'} ({workspace_hash or 'N/A'})")
        print(f"    Target:    {'EXISTS' if target_exists else 'MISSING'} ({target_hash or 'N/A'})")
        
        if status == "❌":
            print(f"    >>> FILES ARE DIFFERENT! <<<")
        elif status == "🚫":
            print(f"    >>> TARGET FILE MISSING! <<<")
        print()
    
    print("="*60)
    if differences_found:
        print("❌ DIFFERENCES FOUND!")
        print("\nℹ️  Copy commands to sync files:")
        print(f"cd {target_base}")
        for file_path in files_to_compare:
            workspace_file = os.path.join(workspace_base, file_path)
            if os.path.exists(workspace_file):
                print(f"cp {workspace_file} {file_path}")
    else:
        print("✅ All files are identical!")
    
    return not differences_found

def test_target_config():
    """Test config loading in target directory"""
    print("\n🧪 Testing config in target directory...")
    
    target_config = "/home/datdang/working/ai-translation-with-style/config/translation.yaml"
    
    if not os.path.exists(target_config):
        print(f"❌ Config file not found: {target_config}")
        return False
    
    try:
        # Test simple YAML loading
        import yaml
        with open(target_config, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
        
        print(f"✅ YAML loaded successfully")
        print(f"📋 Keys: {list(yaml_data.keys())}")
        
        if 'providers' in yaml_data:
            providers = yaml_data['providers']
            for name, provider_data in providers.items():
                config_data = provider_data.get('config', {})
                print(f"📋 {name} config type: {type(config_data)} = {config_data}")
        
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 Running comparison test...\n")
    
    files_match = compare_files()
    config_ok = test_target_config()
    
    print("\n" + "="*50)
    print("📊 COMPARISON SUMMARY:")
    print(f"  - Files match: {'✅' if files_match else '❌'}")
    print(f"  - Target config: {'✅' if config_ok else '❌'}")
    
    if not files_match:
        print("\n💡 SOLUTION: Copy the different files to fix the issue!")
    
    return 0 if (files_match and config_ok) else 1

if __name__ == "__main__":
    exit(main())