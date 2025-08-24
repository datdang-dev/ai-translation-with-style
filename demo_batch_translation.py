#!/usr/bin/env python3
"""
Simple Batch Translation Demo
Quick demo of batch translation functionality
"""

import asyncio
import sys
import os

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from applet.batch_orchestrator import run_batch_translation_from_directory

async def main():
    """Simple batch translation demo"""
    print("🚀 Simple Batch Translation Demo")
    print("=" * 40)
    
    # Configuration
    config_path = "config/preset_translation.json"
    input_dir = "testing_playground"
    output_dir = "testing_playground/batch_output"
    
    print(f"📁 Input: {input_dir}")
    print(f"📁 Output: {output_dir}")
    print(f"🔍 Pattern: chunk_*.json")
    print(f"⚙️  Max concurrent: 2")
    print()
    
    try:
        # Run batch translation
        summary = await run_batch_translation_from_directory(
            config_path=config_path,
            input_dir=input_dir,
            output_dir=output_dir,
            pattern="chunk_*.json",
            max_concurrent=100, # 20 is the max concurrent requests allowed by the API but reserve 2 to avoid rate limit
            job_delay=10.0  # 10-second delay between jobs to avoid API key limiting
        )
        
        # Display results
        print("📊 RESULTS")
        print("-" * 20)
        print(f"✅ Completed: {summary['completed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⏱️  Total time: {summary['total_time']:.2f}s")
        print(f"📈 Success rate: {summary['success_rate']:.1%}")
        
        if summary['completed'] > 0:
            print(f"\n🎉 Successfully translated {summary['completed']} files!")
            print(f"📂 Check output in: {output_dir}")
        elif summary['total_jobs'] == 0:
            print(f"\n⚠️  No files found matching pattern: chunk_*.json")
            print(f"📁 Check if files exist in: {input_dir}")
        else:
            print(f"\n❌ No files were successfully translated")
            print(f"📋 Check error details above")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"📋 Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main())
