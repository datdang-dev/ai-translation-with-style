import asyncio
import json
import copy
from typing import Dict, Any
from services.key_manager.key_manager import APIKeyManager
from services.request_handler.request_handler import RequestHandler
from services.common.api_client import OpenRouterClient
from services.common.logger import get_logger
from services.common.error_codes import ERR_NONE

class TranslationOrchestrator:
    def __init__(self, config_path: str):
        """
        Initialize TranslationOrchestrator
        :param config_path: Path to the preset configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = get_logger("TranslationOrchestrator")
        self.api_key_manager = None
        self.api_client = None
        self.request_handler = None
        self._initialize_services()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load preset configuration file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to read configuration file: {e}")
            raise
    
    def _initialize_services(self):
        """Initialize required services"""
        # Initialize API key manager with keys from config
        api_keys = self.config.get("api_keys", [])
        if not api_keys:
            # Use default key list if not in config
            api_keys = [
                "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",
                "sk-or-v1-7347f7d33b1a8b8d223cede97da38bc928539d13f87c8e8a581ebc7a1f7830",
                "sk-or-v1-70564b801719235882049dd673825c64b4c7e05699a9009ba0d7fccf1b87f",
                "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",
                "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",
                "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",
                "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",
                "sk-or-v1-34ace24dab5d6b2d552103d46e5e035b2e4bf7d43f49d694dc169468b6401c0"
            ]
        
        # Pass required parameters to APIKeyManager
        max_retries = self.config.get("max_retries", 3)
        backoff_base = self.config.get("backoff_base", 2.0)
        max_requests_per_minute = self.config.get("max_requests_per_minute", 20)
        
        self.api_key_manager = APIKeyManager(
            api_keys, 
            max_retries=max_retries,
            backoff_base=backoff_base,
            max_requests_per_minute=max_requests_per_minute
        )
        
        # Initialize API client
        api_url = self.config.get("api_url", "https://openrouter.ai/api/v1/chat/completions")
        self.api_client = OpenRouterClient(self.api_key_manager, api_url, self.logger)
        
        # Initialize request handler
        handler_config = {
            "max_retries": self.config.get("max_retries", 3),
            "backoff_base": self.config.get("backoff_base", 2.0)
        }
        self.request_handler = RequestHandler(
            self.api_client, 
            self.api_key_manager, 
            self.logger, 
            handler_config
        )
    
    async def translate_text(self, text_dict: Dict[str, str]) -> Dict[str, str]:
        """
        Translate a text dictionary
        :param text_dict: Dictionary with ID as key and content to translate as value
        :return: Dictionary with ID as key and translated content as value
        """
        try:
            # Create a copy of the preset
            data = copy.deepcopy(self.config)
            
            # Ensure messages exist
            if 'messages' not in data or not isinstance(data['messages'], list):
                data['messages'] = []
            
            # Convert dictionary to JSON string to send to model
            json_text = json.dumps(text_dict, ensure_ascii=False, indent=2)
            
            # Add content to translate to messages
            data['messages'].extend([
                {
                    'role': 'user',
                    'content': "Now below is the text block you must translate, let's begin translate the text inside the triple backticks block: \n "+"\n```\n" + json_text + "\n```\n"
                }
            ])
            
            # Add stream=True to use streaming response
            data['stream'] = True
            
            # Send request with processed data
            error_code, result = await self.request_handler.handle_request(data)
            if error_code == ERR_NONE:
                # Process API response to return in correct format
                try:
                    # Get translated content from response
                    translated_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # Extract JSON from backticks if present
                    extracted_content = translated_content
                    if translated_content.startswith("```json"):
                        # Remove the starting ```json
                        extracted_content = translated_content[7:]
                        # Remove the ending ```
                        if extracted_content.endswith("```"):
                            extracted_content = extracted_content[:-3]
                    elif translated_content.startswith("```"):
                        # Remove the starting ```
                        extracted_content = translated_content[3:]
                        # Remove the ending ```
                        if extracted_content.endswith("```"):
                            extracted_content = extracted_content[:-3]
                    
                    # Parse JSON string from response
                    try:
                        parsed_json = json.loads(extracted_content)
                        if isinstance(parsed_json, dict):
                            return parsed_json
                        else:
                            # If not a dictionary, return original content
                            return {"error": f"Invalid response format: {translated_content}"}
                    except json.JSONDecodeError:
                        # If not a JSON string, return error
                        return {"error": f"Failed to parse JSON response: {translated_content}"}
                except Exception as e:
                    self.logger.error(f"Error processing API response: {e}")
                    return {"error": f"Failed to process API response: {str(e)}"}
            else:
                self.logger.error(f"Error translating text: {error_code}")
                return {"error": f"Translation failed with error code: {error_code}"}
        except Exception as e:
            self.logger.error(f"Unknown error while translating text: {e}")
            return {"error": f"Translation failed with exception: {str(e)}"}
    
    async def translate_file(self, input_path: str, output_path: str) -> bool:
        """
        Translate entire input file and save result to output
        :param input_path: Input file path
        :param output_path: Output file path
        :return: True if successful, False if failed
        """
        try:
            # Read input file with utf-8-sig encoding to handle BOM
            try:
                with open(input_path, 'r', encoding='utf-8-sig') as f:
                    input_data = json.load(f)
            except UnicodeDecodeError:
                # If utf-8-sig doesn't work, try utf-8
                with open(input_path, 'r', encoding='utf-8') as f:
                    input_data = json.load(f)
            
            # Check if input_data is a dictionary
            if isinstance(input_data, dict):
                # Translate entire dictionary
                result = await self.translate_text(input_data)
                translated_data = result
            else:
                self.logger.error("Invalid input file format")
                return False
            
            # Save result to output file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(translated_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Saved translation result to {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error translating file: {e}")
            return False

# Utility function to run orchestrator
async def run_translation(config_path: str, input_path: str, output_path: str):
    """
    Utility function to run translation process
    :param config_path: Configuration file path
    :param input_path: Input file path
    :param output_path: Output file path
    """
    orchestrator = TranslationOrchestrator(config_path)
    return await orchestrator.translate_file(input_path, output_path)