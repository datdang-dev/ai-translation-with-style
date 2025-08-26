"""
Core translation functionality
"""

import asyncio
import json
import copy
from typing import Dict, Any

from services.key_manager.key_manager import APIKeyManager
from services.request_handler.request_handler import RequestHandler
from services.common.api_client import OpenRouterClient
from services.common.logger import get_logger
from services.common.error_codes import ERR_NONE
from services.translation_service.service_initializer import ServiceInitializer
from services.translation_service.json_parser import JSONParser


class TranslationCore:
    def __init__(self, config_path: str):
        """
        Initialize TranslationCore
        :param config_path: Path to the preset configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = get_logger("TranslationCore")
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
        """Initialize required services using ServiceInitializer"""
        # Create service initializer
        service_initializer = ServiceInitializer(self.config_path, self.logger)
        
        # Initialize all services
        self.api_key_manager, self.api_client, self.request_handler = service_initializer.initialize_all_services()
    
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
            if self.request_handler is None:
                self.logger.error("Request handler not initialized")
                return {"error": "Request handler not initialized"}
                
            error_code, result = await self.request_handler.handle_request(data)
            if error_code == ERR_NONE:
                # Process API response to return in correct format
                try:
                    # Get translated content from response
                    if result is None:
                        self.logger.error("Received None result from API")
                        return {"error": "Received None result from API"}
                    translated_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # Use JSONParser to parse the response with error recovery
                    json_parser = JSONParser()
                    return json_parser.parse_response(translated_content)
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