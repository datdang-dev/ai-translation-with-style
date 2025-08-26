#!/usr/bin/env python3
import asyncio
import os
from pathlib import Path

from applet.translation_orchestrator import run_batch_translation_from_directory

CONFIG_PATH = str(Path(__file__).resolve().parent / "config" / "preset_translation.json")
INPUT_DIR = str(Path(__file__).resolve().parent)
OUTPUT_DIR = str(Path(__file__).resolve().parent / "output")
PATTERN = "playground/chunk_*.json"
MAX_CONCURRENT = 1  # ensure single worker; stagger via job_delay
JOB_DELAY_SECONDS = 10.0  # start next job every 10s, like legacy behavior

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Starting batch translation...")
    print(f"Config: {CONFIG_PATH}")
    print(f"Input:  {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Pattern: {PATTERN}")
    print(f"Concurrency: {MAX_CONCURRENT}, Job delay: {JOB_DELAY_SECONDS}s")

    summary = await run_batch_translation_from_directory(
        config_path=CONFIG_PATH,
        input_dir=INPUT_DIR,
        output_dir=OUTPUT_DIR,
        pattern=PATTERN,
        max_concurrent=MAX_CONCURRENT,
        job_delay=JOB_DELAY_SECONDS,
    )

    print("\nBatch summary:\n", summary)

if __name__ == "__main__":
    asyncio.run(main())
