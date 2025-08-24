#!/usr/bin/env python3
"""
Demo Script for Translation Monitor GUI
Shows the GUI in action with sample data
"""

import os
import sys
import json
from pathlib import Path

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_demo_files():
    """Create demo files for testing"""
    demo_dir = Path("demo_data")
    demo_dir.mkdir(exist_ok=True)
    
    # Create input directory
    input_dir = demo_dir / "input"
    input_dir.mkdir(exist_ok=True)
    
    # Create output directory  
    output_dir = demo_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Create sample chunk files
    sample_chunks = [
        {
            "id": "chunk_001",
            "text": "Hello world! This is a sample text for translation.",
            "source_lang": "en",
            "target_lang": "vi"
        },
        {
            "id": "chunk_002", 
            "text": "Machine learning and artificial intelligence are transforming our world.",
            "source_lang": "en",
            "target_lang": "vi"
        },
        {
            "id": "chunk_003",
            "text": "The quick brown fox jumps over the lazy dog.",
            "source_lang": "en", 
            "target_lang": "vi"
        },
        {
            "id": "chunk_004",
            "text": "Technology advances have revolutionized communication and commerce.",
            "source_lang": "en",
            "target_lang": "vi"
        },
        {
            "id": "chunk_005",
            "text": "Software development requires creativity, logic, and continuous learning.",
            "source_lang": "en",
            "target_lang": "vi"
        }
    ]
    
    # Write chunk files
    for i, chunk in enumerate(sample_chunks, 1):
        chunk_file = input_dir / f"chunk_{i:03d}.json"
        with open(chunk_file, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, indent=2, ensure_ascii=False)
            
    print(f"Created {len(sample_chunks)} demo files in {input_dir}")
    
    # Create demo configuration
    demo_config = {
        "translation_service": "demo",
        "api_key": "demo_key",
        "model": "demo_model",
        "source_language": "en",
        "target_language": "vi",
        "batch_size": 1,
        "timeout": 30
    }
    
    config_dir = demo_dir / "config"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "demo_preset.json"
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(demo_config, f, indent=2)
        
    print(f"Created demo configuration at {config_file}")
    
    return str(input_dir), str(output_dir), str(config_file)

def main():
    """Main demo function"""
    print("🚀 Translation Monitor GUI Demo")
    print("=" * 40)
    
    # Create demo files
    input_dir, output_dir, config_file = create_demo_files()
    
    print(f"\n📁 Demo files created:")
    print(f"   Input directory: {input_dir}")
    print(f"   Output directory: {output_dir}")
    print(f"   Config file: {config_file}")
    
    print(f"\n🎯 Demo Instructions:")
    print(f"1. The GUI will open with pre-configured demo settings")
    print(f"2. Click 'Start Batch Translation' to begin")
    print(f"3. Double-click on jobs to open log windows")
    print(f"4. Right-click on jobs for more options")
    print(f"5. Use the menu to save/load configurations")
    
    # Import and launch GUI
    try:
        from translation_monitor_gui import TranslationMonitorGUI
        
        # Create GUI instance
        app = TranslationMonitorGUI()
        
        # Pre-configure with demo settings
        app.config_var.set(config_file)
        app.input_dir_var.set(input_dir)
        app.output_dir_var.set(output_dir)
        app.pattern_var.set("chunk_*.json")
        app.max_concurrent_var.set("2")
        app.job_delay_var.set("3.0")
        
        print(f"\n🎉 Launching GUI...")
        print(f"   - Configuration: {config_file}")
        print(f"   - Input files: {len(list(Path(input_dir).glob('chunk_*.json')))} files")
        print(f"   - Max concurrent: 2")
        print(f"   - Job delay: 3.0 seconds")
        
        # Run the application
        app.run()
        
    except ImportError as e:
        print(f"❌ Error importing GUI: {e}")
        print(f"Please ensure all dependencies are installed:")
        print(f"   - tkinter (usually comes with Python)")
        print(f"   - All modules in requirements.txt")
        
    except Exception as e:
        print(f"❌ Error launching GUI: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()