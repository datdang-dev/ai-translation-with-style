"""
JSON parser for handling responses from the translation API with error recovery capabilities
"""

import json
import re
from typing import Dict, Any, Union
from services.common.logger import get_logger


class JSONParser:
    """Handles parsing JSON responses from the translation API with multiple recovery strategies"""
    
    def __init__(self):
        """Initialize JSONParser with logger"""
        self.logger = get_logger("JSONParser")
    
    def parse_response(self, response_content: str) -> Dict[str, Any]:
        """
        Parse JSON response from translation API with multiple recovery strategies
        :param response_content: Raw response content from API
        :return: Parsed dictionary or error dictionary
        """
        try:
            # Extract JSON from backticks if present
            extracted_content = response_content
            # Handle cases where JSON is wrapped in backticks with or without json specifier
            stripped_content = response_content.strip()
            if stripped_content.startswith("```json"):
                # Remove the starting ```json
                extracted_content = stripped_content[7:]
                # Remove the ending ``` if present
                extracted_content = extracted_content.strip()
                if extracted_content.endswith("```"):
                    extracted_content = extracted_content[:-3]
            elif stripped_content.startswith("```"):
                # Remove the starting ```
                extracted_content = stripped_content[3:]
                # Remove the ending ``` if present
                extracted_content = extracted_content.strip()
                if extracted_content.endswith("```"):
                    extracted_content = extracted_content[:-3]
            # Strip whitespace from the extracted content
            extracted_content = extracted_content.strip()
            
            # Try to parse JSON string from response
            try:
                parsed_json = json.loads(extracted_content)
                if isinstance(parsed_json, dict):
                    return parsed_json
                else:
                    # If not a dictionary, return error
                    return {"error": f"Invalid response format: {response_content}"}
            except json.JSONDecodeError as e:
                # If JSON parsing fails, try to recover partial content
                self.logger.warning(f"JSON parsing failed: {e}")
                self.logger.warning(f"Attempting to recover partial JSON content...")
                
                # Try multiple recovery strategies
                recovered_result = self._recover_json(extracted_content)
                if recovered_result:
                    return recovered_result
                else:
                    # If all recovery attempts fail, return error with partial content
                    return {"error": f"Failed to parse JSON response: {response_content}"}
        except Exception as e:
            self.logger.error(f"Error processing API response: {e}")
            return {"error": f"Failed to process API response: {str(e)}"}
    
    def _recover_json(self, content: str) -> Union[Dict[str, Any], None]:
        """
        Attempt to recover JSON content using multiple strategies
        :param content: Extracted content to recover
        :return: Recovered dictionary or None if all strategies fail
        """
        # Method 1: Try to find and extract a valid JSON object from the content
        json_matches = re.findall(r'\{[^{]*(?:\{[^{]*\})*[^}]*\}', content)
        if json_matches:
            # Try to parse the longest match first
            json_matches.sort(key=len, reverse=True)
            for match in json_matches:
                try:
                    # Clean up the match to make it more likely to be valid JSON
                    cleaned_match = match.strip()
                    if cleaned_match.startswith('{') and cleaned_match.endswith('}'):
                        parsed_json = json.loads(cleaned_match)
                        if isinstance(parsed_json, dict):
                            self.logger.info(f"Successfully recovered partial JSON with {len(parsed_json)} items (Method 1)")
                            return parsed_json
                except json.JSONDecodeError:
                    continue
        
        # Method 2: Try to fix common JSON issues
        try:
            # Try to fix truncated JSON by adding missing closing braces/brackets
            fixed_content = content
            # Count opening and closing braces
            open_braces = fixed_content.count('{')
            close_braces = fixed_content.count('}')
            # Add missing closing braces
            if open_braces > close_braces:
                fixed_content += '}' * (open_braces - close_braces)
            
            # Count opening and closing brackets
            open_brackets = fixed_content.count('[')
            close_brackets = fixed_content.count(']')
            # Add missing closing brackets
            if open_brackets > close_brackets:
                fixed_content += ']' * (open_brackets - close_brackets)
            
            # Try to parse the fixed content
            parsed_json = json.loads(fixed_content)
            if isinstance(parsed_json, dict):
                self.logger.info(f"Successfully parsed fixed JSON with {len(parsed_json)} items (Method 2)")
                return parsed_json
        except json.JSONDecodeError:
            pass
        
        # Method 3: Try to extract key-value pairs manually
        try:
            # Look for patterns like "key": "value"
            kv_pairs = re.findall(r'"([^"]+)":\s*"([^"]*)"', content)
            if kv_pairs:
                # Create a dictionary from the key-value pairs
                recovered_dict = {}
                for key, value in kv_pairs:
                    recovered_dict[key] = value
                if recovered_dict:
                    self.logger.info(f"Successfully recovered {len(recovered_dict)} items from key-value pairs (Method 3)")
                    return recovered_dict
        except Exception as recovery_error:
            self.logger.error(f"Recovery method 3 failed: {recovery_error}")
            pass
        
        # All recovery methods failed
        return None