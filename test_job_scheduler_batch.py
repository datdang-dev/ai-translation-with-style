#!/usr/bin/env python3
"""
Test job scheduler with batch translation
"""

import sys
sys.path.append('.')
import asyncio
import json
from services.config.service_factory import ServiceFactory
from services.config.configuration_manager import ConfigurationManager

async def test_batch_with_job_scheduler():
    """Test batch translation with job scheduler and detailed logging"""
    print("🧪 Testing batch translation with job scheduler...")
    
    # Create small test data
    test_data = {
        "1": "Hello",
        "2": "World", 
        "3": "Test",
        "4": "Job",
        "5": "Scheduler"
    }
    
    with open('playground/test_job_scheduler.json', 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Created test file with {len(test_data)} texts")
    
    try:
        # Initialize services
        config_manager = ConfigurationManager('config/translation.yaml')
        factory = ServiceFactory(config_manager)
        
        # Create translation manager with job delay
        translation_manager = factory.get_translation_manager()
        translation_manager.update_configuration(
            max_concurrent=2,  # Allow 2 concurrent jobs
            job_delay=2.0      # 2 second delay between jobs
        )
        
        print("✅ Services initialized with job scheduler")
        
        # Prepare content list
        content_list = [test_data]  # List with single JSON object
        
        print(f"🚀 Starting batch translation with job delay...")
        print(f"   Max concurrent: 2")
        print(f"   Job delay: 2.0 seconds")
        print(f"   Content items: {len(content_list)}")
        
        # Run batch translation
        result = await translation_manager.translate_json_batch(
            content_list=content_list,
            target_lang="vi",
            source_lang="en"
        )
        
        print(f"\n📊 BATCH RESULTS:")
        print(f"   Total requests: {result.total_requests}")
        print(f"   Successful: {result.successful_translations}")
        print(f"   Failed: {result.failed_translations}")
        print(f"   Success rate: {result.success_rate:.1f}%")
        print(f"   Processing time: {result.total_processing_time:.2f}s")
        
        if result.successful_translations > 0:
            print("✅ Job scheduler batch translation works!")
        else:
            print("⚠️ No successful translations, but job scheduler ran")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_batch_with_job_scheduler())