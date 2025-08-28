"""
Batch translation demo using the refactored architecture.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Any

from refactored_orchestrator import RefactoredTranslationOrchestrator


class BatchTranslationDemo:
    """Demonstrates batch translation with the refactored architecture"""
    
    def __init__(self, config_path: str):
        self.orchestrator = RefactoredTranslationOrchestrator(config_path)
        self.results: List[Dict[str, Any]] = []
    
    async def load_chunks_from_directory(self, directory: str, pattern: str = "*.json") -> List[Dict[str, Any]]:
        """Load chunks from directory"""
        chunks = []
        directory_path = Path(directory)
        
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
        """Translate a single chunk"""
        chunk_data = chunk_info["chunk_data"]
        file_path = chunk_info["file_path"]
        
        print(f"🔄 Translating: {Path(file_path).name}")
        
        start_time = time.time()
        result = await self.orchestrator.translate_text(chunk_data["text"])
        duration = time.time() - start_time
        
        if result.success:
            translation_result = {
                "file_path": file_path,
                "original_chunk": chunk_data,
                "translation": result.data["translated_text"],
                "status": "success",
                "duration": duration
            }
            print(f"✅ Success: {Path(file_path).name} ({duration:.2f}s)")
        else:
            translation_result = {
                "file_path": file_path,
                "original_chunk": chunk_data,
                "translation": None,
                "status": "failed",
                "error": result.error_message,
                "duration": duration
            }
            print(f"❌ Failed: {Path(file_path).name} - {result.error_message}")
        
        return translation_result
    
    async def run_batch_translation(self, 
                                   input_dir: str, 
                                   output_dir: str = None,
                                   max_concurrent: int = 3) -> Dict[str, Any]:
        """Run batch translation with concurrency control"""
        print(f"🚀 Starting batch translation from: {input_dir}")
        print(f"📊 Max concurrent: {max_concurrent}")
        
        # Load all chunks
        chunks = await self.load_chunks_from_directory(input_dir, "*.json")
        if not chunks:
            print("⚠️  No chunks found!")
            return {"total": 0, "completed": 0, "failed": 0, "results": []}
        
        print(f"📁 Found {len(chunks)} chunks to translate")
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def translate_with_semaphore(chunk_info):
            async with semaphore:
                return await self.translate_chunk(chunk_info)
        
        # Process all chunks concurrently
        start_time = time.time()
        tasks = [translate_with_semaphore(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Process results
        successful_results = []
        failed_results = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_results.append({"error": str(result), "status": "exception"})
            elif result["status"] == "success":
                successful_results.append(result)
            else:
                failed_results.append(result)
        
        # Save results if output directory specified
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            for result in successful_results:
                if result["status"] == "success":
                    # Create output filename
                    input_filename = Path(result["file_path"]).stem
                    output_file = output_path / f"{input_filename}_translated.json"
                    
                    # Save translated result
                    output_data = {
                        "original": result["original_chunk"],
                        "translated_text": result["translation"],
                        "metadata": {
                            "translation_duration": result["duration"],
                            "translated_at": time.time()
                        }
                    }
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        # Generate summary
        summary = {
            "total": len(chunks),
            "completed": len(successful_results),
            "failed": len(failed_results),
            "success_rate": len(successful_results) / len(chunks) if chunks else 0,
            "total_duration": total_duration,
            "avg_duration_per_chunk": total_duration / len(chunks) if chunks else 0,
            "results": results
        }
        
        return summary


async def main():
    """Demo batch translation"""
    print("🚀 Batch Translation Demo - Refactored Architecture")
    print("=" * 60)
    
    # Initialize demo
    demo = BatchTranslationDemo("config/refactored_demo.json")
    
    try:
        # Run batch translation
        summary = await demo.run_batch_translation(
            input_dir="playground",
            output_dir="playground/batch_output",
            max_concurrent=2
        )
        
        # Display results
        print("\n📊 BATCH TRANSLATION RESULTS")
        print("-" * 40)
        print(f"✅ Total chunks: {summary['total']}")
        print(f"✅ Completed: {summary['completed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"📈 Success rate: {summary['success_rate']:.1%}")
        print(f"⏱️  Total time: {summary['total_duration']:.2f}s")
        print(f"⚡ Avg per chunk: {summary['avg_duration_per_chunk']:.2f}s")
        
        # Show system metrics
        print("\n📊 SYSTEM METRICS")
        print("-" * 40)
        status = await demo.orchestrator.get_system_status()
        key_summary = status['key_management']['summary']
        print(f"🔑 Active keys: {key_summary['active_keys']}/{key_summary['total_keys']}")
        print(f"⚠️  Rate limited: {key_summary['rate_limited_keys']}")
        print(f"❌ Error keys: {key_summary['error_keys']}")
        
        # Show detailed metrics
        metrics = demo.orchestrator.metrics_service.get_metrics()
        print(f"📈 API requests: {metrics['counters'].get('api.request.success', {}).get('value', 0)}")
        print(f"🎯 Translations: {metrics['counters'].get('translation.success', {}).get('value', 0)}")
        
        # Show translation durations
        for name, histogram in metrics['histograms'].items():
            if 'duration' in name and histogram['stats']:
                stats = histogram['stats']
                print(f"⏱️  {name}: {stats['mean']:.3f}s avg (min: {stats['min']:.3f}s, max: {stats['max']:.3f}s)")
        
        if summary['completed'] > 0:
            print(f"\n🎉 Successfully translated {summary['completed']} files!")
            print(f"📂 Check output in: playground/batch_output")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())