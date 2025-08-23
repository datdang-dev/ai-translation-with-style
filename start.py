import asyncio
import sys
import os

# Add current directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import orchestrator
from applet.orchestrator import run_translation

# Configure paths
input_path = "testing_playground/input.json"
output_path = "testing_playground/output.json"
preset_path = "config/preset_translation.json"

async def main():
    """Main function to run translation process"""
    print("Starting translation process...")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Preset: {preset_path}")
    
    try:
        success = await run_translation(preset_path, input_path, output_path)
        if success:
            print("Translation process completed successfully!")
        else:
            print("Translation process failed!")
            return 1
    except Exception as e:
        print(f"Error during translation: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)