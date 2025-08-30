"""
Input Standardizer
Handles conversion of input text from different engine formats to framework standard
"""

import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from services.common.logger import get_logger
from services.common.error_codes import ERR_STANDARDIZATION_FAILED

class StandardizationInterface(ABC):
    """Abstract interface for input standardization"""
    
    @abstractmethod
    def can_handle(self, input_data: Any) -> bool:
        """
        Check if this standardizer can handle the input format
        :param input_data: Input data to check
        :return: True if this standardizer can handle the format
        """
        pass
    
    @abstractmethod
    def standardize(self, input_data: Any) -> Dict[str, str]:
        """
        Convert input to framework standard format
        :param input_data: Input data to standardize
        :return: Standardized dictionary with numeric string keys
        """
        pass
    
    @abstractmethod
    def get_format_name(self) -> str:
        """
        Get the name of the format this standardizer handles
        :return: Format name string
        """
        pass

class JSONStandardizer(StandardizationInterface):
    """Standardizer for JSON input files"""
    
    def __init__(self):
        self.logger = get_logger("JSONStandardizer")
    
    def can_handle(self, input_data: Any) -> bool:
        """Check if input is JSON format"""
        if isinstance(input_data, str):
            try:
                json.loads(input_data)
                return True
            except (json.JSONDecodeError, TypeError):
                return False
        elif isinstance(input_data, dict):
            return True
        return False
    
    def standardize(self, input_data: Any) -> Dict[str, str]:
        """
        Standardize JSON input to framework format
        :param input_data: JSON string or dict
        :return: Standardized dictionary
        """
        try:
            # Parse JSON if it's a string
            if isinstance(input_data, str):
                data = json.loads(input_data)
            else:
                data = input_data
            
            # Convert to standardized format
            standardized = {}
            for key, value in data.items():
                # Ensure key is string and value is string
                str_key = str(key)
                str_value = str(value) if value is not None else ""
                
                # Validate key format (should be numeric)
                try:
                    int(str_key)
                    standardized[str_key] = str_value
                except ValueError:
                    self.logger.warning(f"Skipping non-numeric key: {str_key}")
                    continue
            
            self.logger.info(f"Standardized {len(standardized)} entries from JSON input")
            return standardized
            
        except Exception as e:
            error_msg = f"Failed to standardize JSON input: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def get_format_name(self) -> str:
        return "JSON"

class TextStandardizer(StandardizationInterface):
    """Standardizer for plain text input"""
    
    def __init__(self, delimiter: str = "\n"):
        """
        Initialize text standardizer
        :param delimiter: Delimiter to split text into chunks
        """
        self.delimiter = delimiter
        self.logger = get_logger("TextStandardizer")
    
    def can_handle(self, input_data: Any) -> bool:
        """Check if input is plain text"""
        return isinstance(input_data, str) and not self._looks_like_json(input_data)
    
    def standardize(self, input_data: Any) -> Dict[str, str]:
        """
        Standardize text input to framework format
        :param input_data: Plain text string
        :return: Standardized dictionary
        """
        try:
            if not isinstance(input_data, str):
                raise ValueError("Input must be a string")
            
            # Split text into chunks
            chunks = input_data.split(self.delimiter)
            chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
            
            # Convert to standardized format
            standardized = {}
            for i, chunk in enumerate(chunks):
                standardized[str(i)] = chunk
            
            self.logger.info(f"Standardized {len(standardized)} text chunks")
            return standardized
            
        except Exception as e:
            error_msg = f"Failed to standardize text input: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _looks_like_json(self, text: str) -> bool:
        """Check if text looks like JSON"""
        text = text.strip()
        return (text.startswith('{') and text.endswith('}')) or \
               (text.startswith('[') and text.endswith(']'))
    
    def get_format_name(self) -> str:
        return "Text"

class FileStandardizer(StandardizationInterface):
    """Standardizer for file input (auto-detects format)"""
    
    def __init__(self):
        self.logger = get_logger("FileStandardizer")
        self.json_standardizer = JSONStandardizer()
        self.text_standardizer = TextStandardizer()
    
    def can_handle(self, input_data: Any) -> bool:
        """Check if input is a file path"""
        if isinstance(input_data, (str, Path)):
            path = Path(input_data)
            return path.exists() and path.is_file()
        return False
    
    def standardize(self, input_data: Any) -> Dict[str, str]:
        """
        Standardize file input to framework format
        :param input_data: File path
        :return: Standardized dictionary
        """
        try:
            path = Path(input_data)
            
            # Read file content
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Auto-detect format and use appropriate standardizer
            if self.json_standardizer.can_handle(content):
                self.logger.info(f"Detected JSON format in {path}")
                return self.json_standardizer.standardize(content)
            elif self.text_standardizer.can_handle(content):
                self.logger.info(f"Detected text format in {path}")
                return self.text_standardizer.standardize(content)
            else:
                # Try to treat as text as fallback
                self.logger.warning(f"Unknown format in {path}, treating as text")
                return self.text_standardizer.standardize(content)
                
        except Exception as e:
            error_msg = f"Failed to standardize file input {input_data}: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def get_format_name(self) -> str:
        return "File"

class Standardizer:
    """Main standardizer class that manages multiple standardization strategies"""
    
    def __init__(self, auto_convert: bool = True):
        """
        Initialize standardizer
        :param auto_convert: Whether to automatically convert input formats
        """
        self.auto_convert = auto_convert
        self.logger = get_logger("Standardizer")
        
        # Register default standardizers
        self.standardizers: List[StandardizationInterface] = [
            JSONStandardizer(),
            TextStandardizer(),
            FileStandardizer()
        ]
    
    def add_standardizer(self, standardizer: StandardizationInterface) -> None:
        """
        Add a custom standardizer
        :param standardizer: Custom standardizer implementation
        """
        self.standardizers.append(standardizer)
        self.logger.info(f"Added custom standardizer: {type(standardizer).__name__}")
    
    def standardize(self, input_data: Any, force_format: Optional[str] = None) -> Dict[str, str]:
        """
        Standardize input data to framework format
        :param input_data: Input data to standardize
        :param force_format: Force specific format (optional)
        :return: Standardized dictionary
        """
        try:
            # If auto-convert is disabled and input is already in correct format, return as-is
            if not self.auto_convert and self._is_already_standardized(input_data):
                self.logger.info("Input already in standard format, skipping conversion")
                return input_data
            
            # Find appropriate standardizer
            standardizer = self._find_standardizer(input_data, force_format)
            
            if not standardizer:
                raise ValueError(f"No standardizer found for input type: {type(input_data).__name__}")
            
            # Perform standardization
            self.logger.info(f"Using {standardizer.get_format_name()} standardizer")
            return standardizer.standardize(input_data)
            
        except Exception as e:
            error_msg = f"Standardization failed: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _find_standardizer(self, input_data: Any, force_format: Optional[str] = None) -> Optional[StandardizationInterface]:
        """
        Find appropriate standardizer for input data
        :param input_data: Input data
        :param force_format: Force specific format
        :return: Appropriate standardizer or None
        """
        if force_format:
            # Find standardizer by format name
            for standardizer in self.standardizers:
                if standardizer.get_format_name().lower() == force_format.lower():
                    return standardizer
            return None
        
        # Auto-detect format
        for standardizer in self.standardizers:
            if standardizer.can_handle(input_data):
                return standardizer
        
        return None
    
    def _is_already_standardized(self, input_data: Any) -> bool:
        """
        Check if input is already in standardized format
        :param input_data: Input data to check
        :return: True if already standardized
        """
        if not isinstance(input_data, dict):
            return False
        
        # Check if all keys are numeric strings
        for key in input_data.keys():
            if not isinstance(key, str):
                return False
            try:
                int(key)
            except ValueError:
                return False
        
        return True
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported input formats
        :return: List of format names
        """
        return [std.get_format_name() for std in self.standardizers]
    
    def get_standardization_stats(self) -> Dict[str, Any]:
        """
        Get standardization statistics
        :return: Dictionary with standardization statistics
        """
        return {
            "auto_convert": self.auto_convert,
            "supported_formats": self.get_supported_formats(),
            "total_standardizers": len(self.standardizers)
        }