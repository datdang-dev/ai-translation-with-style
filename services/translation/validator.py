"""
Response Validator
Handles validation of AI responses using strategy pattern
"""

import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
from services.common.logger import get_logger
from services.common.error_codes import ERR_VALIDATION_FAILED

class ValidationStrategy(ABC):
    """Abstract base class for validation strategies"""
    
    @abstractmethod
    def validate(self, response: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate the response
        :param response: Raw response string to validate
        :return: Tuple of (is_valid, error_message, parsed_data)
        """
        pass

class JSONValidationStrategy(ValidationStrategy):
    """Strategy for validating JSON responses"""
    
    def __init__(self, strict: bool = True, allow_partial: bool = False):
        """
        Initialize JSON validation strategy
        :param strict: Whether to enforce strict JSON validation
        :param allow_partial: Whether to allow partial JSON responses
        """
        self.strict = strict
        self.allow_partial = allow_partial
        self.logger = get_logger("JSONValidationStrategy")
    
    def validate(self, response: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate JSON response
        :param response: Raw response string to validate
        :return: Tuple of (is_valid, error_message, parsed_data)
        """
        try:
            # Clean the response
            cleaned_response = self._clean_response(response)
            
            # Try to parse as JSON
            parsed_data = json.loads(cleaned_response)
            
            # Additional validation if strict mode
            if self.strict:
                validation_result = self._strict_validation(parsed_data)
                if not validation_result[0]:
                    return validation_result
            
            return True, None, parsed_data
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON format: {str(e)}"
            self.logger.warning(f"JSON validation failed: {error_msg}")
            return False, error_msg, None
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            self.logger.error(f"Unexpected validation error: {error_msg}")
            return False, error_msg, None
    
    def _clean_response(self, response: str) -> str:
        """
        Clean the response string before parsing
        :param response: Raw response string
        :return: Cleaned response string
        """
        # Remove common prefixes/suffixes that might be added by AI
        response = response.strip()
        
        # Remove markdown code blocks if present
        response = re.sub(r'^```json\s*', '', response)
        response = re.sub(r'\s*```$', '', response)
        
        # Remove extra text before/after JSON
        lines = response.split('\n')
        json_lines = []
        in_json = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('{') or line.startswith('['):
                in_json = True
            if in_json:
                json_lines.append(line)
            if line.endswith('}') or line.endswith(']'):
                break
        
        if json_lines:
            return '\n'.join(json_lines)
        
        return response
    
    def _strict_validation(self, data: Any) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Perform strict validation on parsed data
        :param data: Parsed JSON data
        :return: Tuple of (is_valid, error_message, parsed_data)
        """
        # Check if it's a dictionary (expected format)
        if not isinstance(data, dict):
            return False, "Response must be a JSON object", None
        
        # Check for required structure (should have numeric keys)
        if not data:
            return False, "Response cannot be empty", None
        
        # Validate that keys are strings (JSON requirement) and can be converted to numbers
        for key in data.keys():
            if not isinstance(key, str):
                return False, f"Invalid key type: {type(key).__name__}, expected string", None
            
            try:
                int(key)  # Try to convert to number
            except ValueError:
                return False, f"Invalid key format: '{key}', expected numeric string", None
        
        return True, None, data

class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message: str, error_type: str = "validation"):
        self.message = message
        self.error_type = error_type
        super().__init__(self.message)

class Validator:
    """Main validator class that uses strategy pattern"""
    
    def __init__(self, strategy: ValidationStrategy = None):
        """
        Initialize validator with a validation strategy
        :param strategy: Validation strategy to use (defaults to JSONValidationStrategy)
        """
        self.strategy = strategy or JSONValidationStrategy()
        self.logger = get_logger("Validator")
    
    def set_strategy(self, strategy: ValidationStrategy) -> None:
        """
        Change the validation strategy
        :param strategy: New validation strategy
        """
        self.strategy = strategy
        self.logger.info(f"Validation strategy changed to: {type(strategy).__name__}")
    
    def validate(self, response: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate response using current strategy
        :param response: Raw response string to validate
        :return: Tuple of (is_valid, error_message, parsed_data)
        """
        if not self.strategy:
            raise ValueError("No validation strategy set")
        
        return self.strategy.validate(response)
    
    def validate_and_raise(self, response: str) -> Dict[str, Any]:
        """
        Validate response and raise exception if invalid
        :param response: Raw response string to validate
        :return: Parsed data if valid
        :raises: ValidationError if validation fails
        """
        is_valid, error_msg, parsed_data = self.validate(response)
        
        if not is_valid:
            raise ValidationError(error_msg or "Validation failed")
        
        return parsed_data
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics
        :return: Dictionary with validation statistics
        """
        if hasattr(self.strategy, 'get_stats'):
            return self.strategy.get_stats()
        return {"strategy": type(self.strategy).__name__}