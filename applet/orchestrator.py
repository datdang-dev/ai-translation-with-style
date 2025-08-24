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
            # Try to load API keys from external file
            try:
                api_keys_path = "config/api_keys.json"
                with open(api_keys_path, 'r', encoding='utf-8') as f:
                    api_keys_config = json.load(f)
                    api_keys = api_keys_config.get("api_keys", [])
                self.logger.info(f"Loaded {len(api_keys)} API keys from {api_keys_path}")
            except FileNotFoundError:
                self.logger.warning(f"API keys file not found at {api_keys_path}")
                api_keys = []
            except Exception as e:
                self.logger.error(f"Error loading API keys: {e}")
                api_keys = []
        
        if not api_keys:
            self.logger.error("No API keys available. Please configure API keys in config/api_keys.json")
            raise ValueError("No API keys available")
        
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
                    # Handle cases where JSON is wrapped in backticks with or without json specifier
                    stripped_content = translated_content.strip()
                    if stripped_content.startswith("```json"):
                        # Remove the starting ```json
                        extracted_content = stripped_content[7:]
                        # Remove the ending ```
                        if extracted_content.strip().endswith("```"):
                            extracted_content = extracted_content.strip()[:-3]
                    elif stripped_content.startswith("```"):
                        # Remove the starting ```
                        extracted_content = stripped_content[3:]
                        # Remove the ending ```
                        if extracted_content.strip().endswith("```"):
                            extracted_content = extracted_content.strip()[:-3]
                    # Strip whitespace from the extracted content
                    extracted_content = extracted_content.strip()
                    
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