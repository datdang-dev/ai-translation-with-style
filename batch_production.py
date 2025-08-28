"""
Batch production translation with real API keys.
"""

import asyncio
import json
import time
import os
from pathlib import Path
from typing import List, Dict, Any

from production_orchestrator import ProductionTranslationOrchestrator


class BatchProductionTranslation:
    """Production batch translation with real API integration"""
    
    def __init__(self, config_path: str = "config/production_config.json"):
        self.orchestrator = ProductionTranslationOrchestrator(config_path)
        self.results: List[Dict[str, Any]] = []
    
    async def load_chunks_from_directory(self, directory: str, pattern: str = "*.json") -> List[Dict[str, Any]]:
        """Load chunks from directory"""
        chunks = []
        directory_path = Path(directory)
        
        if not directory_path.exists():
            print(f"❌ Directory not found: {directory}")
            return chunks
        
        for file_path in directory_path.glob(pattern):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    chunk_data = json.load(f)
                    chunks.append({
                        "file_path": str(file_path),
                        "chunk_data": chunk_data
                    })
            except Exception as e:
                print(f"❌ Error loading {file_path}: {e}")
        
        return chunks
    
    async def translate_chunk(self, chunk_info: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a single chunk with production API"""
        chunk_data = chunk_info["chunk_data"]
        file_path = chunk_info["file_path"]
        filename = Path(file_path).name
        
        print(f"🔄 Translating: {filename}")
        
        start_time = time.time()
        result = await self.orchestrator.translate_text(chunk_data["text"])
        duration = time.time() - start_time
        
        if result.success:
            translation_result = {
                "file_path": file_path,
                "original_chunk": chunk_data,
                "translation": result.data["translated_text"],
                "usage": result.data.get("usage", {}),
                "status": "success",
                "duration": duration
            }
            
            usage = result.data.get("usage", {})
            token_info = f" ({usage.get('total_tokens', 0)} tokens)" if usage else ""
            print(f"✅ {filename} completed{token_info} ({duration:.2f}s)")
            
        else:
            translation_result = {
                "file_path": file_path,
                "original_chunk": chunk_data,
                "translation": None,
                "status": "failed",
                "error": result.error_message,
                "duration": duration
            }
            print(f"❌ {filename} failed: {result.error_message}")
        
        return translation_result
    
    async def run_batch_translation(self, 
                                   input_dir: str, 
                                   output_dir: str = None,
                                   max_concurrent: int = 2,
                                   delay_between_batches: float = 1.0) -> Dict[str, Any]:
        """Run production batch translation with rate limiting"""
        
        print(f"🚀 Production Batch Translation")
        print(f"📁 Input: {input_dir}")
        print(f"📁 Output: {output_dir or 'console only'}")
        print(f"🔄 Max concurrent: {max_concurrent}")
        print(f"⏱️  Delay between batches: {delay_between_batches}s")
        
        # Load all chunks
        chunks = await self.load_chunks_from_directory(input_dir)
        if not chunks:
            return {"total": 0, "completed": 0, "failed": 0, "results": []}
        
        print(f"📊 Found {len(chunks)} chunks to translate")
        
        # Process in batches to respect rate limits
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def translate_with_semaphore(chunk_info):
            async with semaphore:
                result = await self.translate_chunk(chunk_info)
                # Add delay between requests to avoid rate limiting
                await asyncio.sleep(delay_between_batches)
                return result
        
        # Process all chunks
        start_time = time.time()
        print(f"\n🏃‍♂️ Starting translation...")
        
        tasks = [translate_with_semaphore(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        
        # Process results
        successful_results = []
        failed_results = []
        total_tokens = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed_results.append({"error": str(result), "status": "exception"})
            elif result["status"] == "success":
                successful_results.append(result)
                total_tokens += result.get("usage", {}).get("total_tokens", 0)
            else:
                failed_results.append(result)
        
        # Save results if output directory specified
        if output_dir and successful_results:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            print(f"\n💾 Saving results to {output_dir}...")
            
            for result in successful_results:
                if result["status"] == "success":
                    input_filename = Path(result["file_path"]).stem
                    output_file = output_path / f"{input_filename}_translated.json"
                    
                    output_data = {
                        "original": result["original_chunk"],
                        "translated_text": result["translation"],
                        "metadata": {
                            "translation_duration": result["duration"],
                            "token_usage": result.get("usage", {}),
                            "translated_at": time.time(),
                            "model": self.orchestrator.config_service.get("model")
                        }
                    }
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        # Generate comprehensive summary
        summary = {
            "total": len(chunks),
            "completed": len(successful_results),
            "failed": len(failed_results),
            "success_rate": len(successful_results) / len(chunks) if chunks else 0,
            "total_duration": total_duration,
            "avg_duration_per_chunk": total_duration / len(chunks) if chunks else 0,
            "total_tokens_used": total_tokens,
            "estimated_cost_usd": total_tokens * 0.000001,  # Rough estimate
            "results": results
        }
        
        return summary


async def main():
    """Run production batch translation"""
    print("🚀 Production Batch Translation Service")
    print("=" * 60)
    
    # Check for API keys
    if not os.path.exists("config/api_keys.json"):
        print("❌ API keys not configured!")
        print("Run: python3 setup_api_keys.py")
        return
    
    try:
        # Initialize batch processor
        batch_processor = BatchProductionTranslation()
        
        # Configuration
        input_dir = "playground"
        output_dir = "playground/production_output"
        max_concurrent = 2  # Conservative for rate limiting
        delay_between_batches = 2.0  # 2 second delay between requests
        
        # Run batch translation
        summary = await batch_processor.run_batch_translation(
            input_dir=input_dir,
            output_dir=output_dir,
            max_concurrent=max_concurrent,
            delay_between_batches=delay_between_batches
        )
        
        # Display comprehensive results
        print(f"\n📊 BATCH TRANSLATION RESULTS")
        print("=" * 60)
        print(f"✅ Total files: {summary['total']}")
        print(f"✅ Completed: {summary['completed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"📈 Success rate: {summary['success_rate']:.1%}")
        print(f"⏱️  Total time: {summary['total_duration']:.1f}s")
        print(f"⚡ Avg per file: {summary['avg_duration_per_chunk']:.1f}s")
        print(f"🪙 Total tokens: {summary['total_tokens_used']:,}")
        print(f"💰 Estimated cost: ${summary['estimated_cost_usd']:.4f}")
        
        # Show system status
        print(f"\n📊 SYSTEM STATUS")
        print("-" * 40)
        status = await batch_processor.orchestrator.get_detailed_status()
        perf = status["performance"]
        keys = status["key_management"]["summary"]
        
        print(f"🔑 Active keys: {keys['active_keys']}/{keys['total_keys']}")
        print(f"⚠️  Rate limited: {keys['rate_limited_keys']}")
        print(f"❌ Error keys: {keys['error_keys']}")
        print(f"📈 Overall success rate: {perf['success_rate_percent']:.1f}%")
        
        if summary['completed'] > 0:
            print(f"\n🎉 Successfully translated {summary['completed']} files!")
            print(f"📂 Results saved to: {output_dir}")
        
        # Show per-key usage
        print(f"\n🔑 API Key Usage:")
        key_details = status['key_management']['keys']['keys']
        for key_info in key_details:
            status_icon = "✅" if key_info['status'] == 'active' else "⚠️"
            print(f"   {status_icon} {key_info['name']}: {key_info['total_requests']} requests")
        
    except KeyboardInterrupt:
        print("\n⏹️  Batch processing stopped by user")
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())