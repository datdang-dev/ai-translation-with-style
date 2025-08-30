#!/usr/bin/env python3
"""
Refactored Translation Framework Application
Uses the new middleware architecture for improved modularity and maintainability
"""

import asyncio
import sys
import os
import time

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from applet import TranslationApplet

async def main():
    """Main application entry point"""
    print("🚀 Refactored Translation Framework")
    print("=" * 50)
    
    # Configuration
    config_path = "config/config.yaml"
    input_dir = "playground"
    output_dir = "playground/batch_output"
    
    print(f"📁 Input: {input_dir}")
    print(f"📁 Output: {output_dir}")
    print(f"🔍 Pattern: chunk_*.json")
    print(f"⚙️  Config: {config_path}")
    print()
    
    try:
        # Initialize translation applet
        print("🔧 Initializing translation system...")
        applet = TranslationApplet(config_path)
        
        # Perform health check
        print("🏥 Performing health check...")
        if await applet.health_check():
            print("✅ System is healthy")
        else:
            print("❌ System health check failed")
            return
        
        # Display system information
        print("\n📊 SYSTEM INFORMATION")
        print("-" * 30)
        
        config_summary = applet.get_configuration_summary()
        print(f"🌐 API URL: {config_summary.get('api_config', {}).get('url', 'N/A')}")
        print(f"🤖 Model: {config_summary.get('translation_config', {}).get('model', 'N/A')}")
        print(f"⏱️  Job Delay: {config_summary.get('scheduling_config', {}).get('job_delay', 'N/A')}s")
        print(f"🔄 Max Concurrent: {config_summary.get('scheduling_config', {}).get('max_concurrent', 'N/A')}")
        
        supported_formats = applet.get_supported_formats()
        print(f"📝 Supported Formats: {', '.join(supported_formats)}")
        
        print("\n🚀 Starting batch translation...")
        start_time = time.time()
        
        # Run batch translation
        summary = await applet.translate_batch_from_directory(
            input_dir=input_dir,
            output_dir=output_dir,
            pattern="chunk_*.json"
        )
        
        # Display results
        total_time = time.time() - start_time
        print("\n📊 RESULTS")
        print("-" * 20)
        print(f"✅ Completed: {summary['completed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⏱️  Total time: {total_time:.2f}s")
        print(f"📈 Success rate: {summary['success_rate']:.1%}")
        
        if summary['completed'] > 0:
            print(f"\n🎉 Successfully translated {summary['completed']} files!")
            print(f"📂 Check output in: {output_dir}")
        elif summary['total_jobs'] == 0:
            print(f"\n⚠️  No files found matching pattern: chunk_*.json")
            print(f"📁 Check if files exist in: {input_dir}")
        else:
            print(f"\n❌ No files were successfully translated")
            if 'error' in summary:
                print(f"📋 Error: {summary['error']}")
        
        # Display system status
        print("\n🔍 SYSTEM STATUS")
        print("-" * 20)
        system_status = applet.get_system_status()
        
        if system_status.get('key_manager'):
            key_stats = system_status['key_manager']
            print(f"🔑 API Keys: {key_stats['active_keys']}/{key_stats['total_keys']} active")
            print(f"📊 Key Success Rate: {key_stats['success_rate']:.1f}%")
        
        if system_status.get('scheduler'):
            scheduler_stats = system_status['scheduler']
            print(f"⏰ Scheduler: {'Running' if scheduler_stats['is_running'] else 'Stopped'}")
            print(f"📋 Total Jobs: {scheduler_stats['total_jobs']}")
        
        print(f"\n🎯 Framework: Refactored Architecture")
        print(f"🏗️  Middleware: CoreManager + Services")
        print(f"🔧 Applet: Single TranslationApplet")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"📋 Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main())