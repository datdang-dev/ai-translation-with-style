"""
Format Manager for handling different input/output formats
Supports JSON, TXT, and other formats with format-specific validation
"""

import json
import os
import yaml
from typing import Dict, Any, List, Union, Optional
from abc import ABC, abstractmethod
from services.common.logger import get_logger


class FormatValidator(ABC):
    """Abstract base class for format-specific validators"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    def validate_input(self, content: Any) -> bool:
        """Validate input content for this format"""
        pass
    
    @abstractmethod
    def validate_output(self, content: Any) -> bool:
        """Validate output content for this format"""
        pass
    
    @abstractmethod
    def extract_text(self, content: Any) -> Dict[str, str]:
        """Extract translatable text from content"""
        pass
    
    @abstractmethod
    def reconstruct_content(self, original_content: Any, translated_text: Dict[str, str]) -> Any:
        """Reconstruct content with translated text"""
        pass


class JSONValidator(FormatValidator):
    """JSON format validator and processor"""
    
    def validate_input(self, content: Any) -> bool:
        """Validate JSON input content"""
        if not isinstance(content, dict):
            return False
        
        # Get validation rules from config
        validation_config = self.config.get('validation', {})
        require_string_values = validation_config.get('require_string_values', True)
        allow_empty_keys = validation_config.get('allow_empty_keys', False)
        max_key_length = validation_config.get('max_key_length', 100)
        max_value_length = validation_config.get('max_value_length', 10000)
        
        # Check if it's a text dictionary (string keys with string values)
        for key, value in content.items():
            if not isinstance(key, str):
                return False
            
            if not allow_empty_keys and not key.strip():
                return False
            
            if len(key) > max_key_length:
                return False
            
            if require_string_values:
                if not isinstance(value, str):
                    return False
                if len(value) > max_value_length:
                    return False
        
        return True
    
    def validate_output(self, content: Any) -> bool:
        """Validate JSON output content"""
        return self.validate_input(content)
    
    def extract_text(self, content: Dict[str, str]) -> Dict[str, str]:
        """Extract text from JSON dictionary"""
        return content.copy()
    
    def reconstruct_content(self, original_content: Dict[str, str], translated_text: Dict[str, str]) -> Dict[str, str]:
        """Reconstruct JSON with translated text"""
        # Merge original structure with translated text
        result = {}
        for key in original_content:
            if key in translated_text:
                result[key] = translated_text[key]
            else:
                # Keep original if translation missing
                result[key] = original_content[key]
        return result


class TXTValidator(FormatValidator):
    """Plain text format validator and processor"""
    
    def validate_input(self, content: Any) -> bool:
        """Validate text input content"""
        if not isinstance(content, str):
            return False
        
        validation_config = self.config.get('validation', {})
        max_line_length = validation_config.get('max_line_length', 1000)
        allow_empty_lines = validation_config.get('allow_empty_lines', True)
        
        lines = content.strip().split('\n')
        for line in lines:
            if not allow_empty_lines and not line.strip():
                return False
            if len(line) > max_line_length:
                return False
        
        return len(content.strip()) > 0
    
    def validate_output(self, content: Any) -> bool:
        """Validate text output content"""
        return self.validate_input(content)
    
    def extract_text(self, content: str) -> Dict[str, str]:
        """Extract text from string content"""
        # Split by lines and create numbered entries
        lines = content.strip().split('\n')
        text_dict = {}
        for i, line in enumerate(lines):
            if line.strip():  # Skip empty lines
                text_dict[str(i)] = line.strip()
        return text_dict
    
    def reconstruct_content(self, original_content: str, translated_text: Dict[str, str]) -> str:
        """Reconstruct text with translated content"""
        # Reconstruct text from translated dictionary
        lines = []
        for i in range(len(translated_text)):
            key = str(i)
            if key in translated_text:
                lines.append(translated_text[key])
            else:
                # Keep original if translation missing
                original_lines = original_content.strip().split('\n')
                if i < len(original_lines):
                    lines.append(original_lines[i])
        
        return '\n'.join(lines)


class FormatManager:
    """Manages different input/output formats and their validators"""
    
    def __init__(self, config_path: str = None):
        self.logger = get_logger("FormatManager")
        self.config = self._load_config(config_path)
        self.validators = self._initialize_validators()
        self.default_format = self.config.get('formats', {}).get('default', 'json')
    
    def _load_config(self, config_path: str = None) -> Dict[str, Any]:
        """Load configuration file"""
        if config_path is None:
            config_path = "config/translation_config.yaml"
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                        return yaml.safe_load(f) or {}
                    else:
                        return json.load(f) or {}
            else:
                self.logger.warning(f"Config file not found: {config_path}, using defaults")
                return {}
        except Exception as e:
            self.logger.warning(f"Failed to load config: {e}, using defaults")
            return {}
    
    def _initialize_validators(self) -> Dict[str, FormatValidator]:
        """Initialize validators based on configuration"""
        validators = {}
        formats_config = self.config.get('formats', {}).get('supported', {})
        
        # Initialize JSON validator
        if formats_config.get('json', {}).get('enabled', True):
            validators['json'] = JSONValidator(formats_config.get('json', {}))
        
        # Initialize TXT validator
        if formats_config.get('txt', {}).get('enabled', True):
            validators['txt'] = TXTValidator(formats_config.get('txt', {}))
        
        # Initialize TEXT validator (alias for TXT)
        if formats_config.get('text', {}).get('enabled', True):
            validators['text'] = TXTValidator(formats_config.get('text', {}))
        
        # Ensure at least JSON validator is available
        if not validators:
            self.logger.warning("No validators configured, using default JSON validator")
            validators['json'] = JSONValidator()
        
        return validators
    
    def detect_format(self, file_path: str) -> str:
        """Detect format from file extension"""
        _, ext = os.path.splitext(file_path.lower())
        if ext == '.json':
            return 'json'
        elif ext in ['.txt', '.text']:
            return 'txt'
        else:
            # Default to configured default format
            return self.default_format
    
    def get_validator(self, format_type: str) -> FormatValidator:
        """Get validator for specified format"""
        if format_type not in self.validators:
            self.logger.warning(f"Unknown format '{format_type}', using default '{self.default_format}'")
            format_type = self.default_format
        
        return self.validators[format_type]
    
    def load_content(self, file_path: str, format_type: Optional[str] = None) -> tuple[Any, str]:
        """Load content from file based on format"""
        if format_type is None:
            format_type = self.detect_format(file_path)
        
        validator = self.get_validator(format_type)
        
        try:
            # Read file with appropriate encoding
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    if format_type == 'json':
                        content = json.load(f)
                    else:
                        content = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='utf-8') as f:
                    if format_type == 'json':
                        content = json.load(f)
                    else:
                        content = f.read()
            
            # Validate input
            if not validator.validate_input(content):
                raise ValueError(f"Invalid {format_type} format for file: {file_path}")
            
            return content, format_type
            
        except Exception as e:
            self.logger.error(f"Error loading {format_type} file {file_path}: {e}")
            raise
    
    def save_content(self, file_path: str, content: Any, format_type: str) -> bool:
        """Save content to file based on format"""
        try:
            validator = self.get_validator(format_type)
            
            # Validate output
            if not validator.validate_output(content):
                self.logger.error(f"Invalid {format_type} output format")
                return False
            
            # Save with appropriate format
            with open(file_path, 'w', encoding='utf-8') as f:
                if format_type == 'json':
                    json.dump(content, f, ensure_ascii=False, indent=2)
                else:
                    f.write(str(content))
            
            self.logger.info(f"Saved {format_type} content to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving {format_type} file {file_path}: {e}")
            return False
    
    def process_translation(self, 
                          input_path: str, 
                          output_path: str, 
                          format_type: Optional[str] = None) -> tuple[Dict[str, str], str]:
        """
        Process translation: load content, extract text, and prepare for reconstruction
        Returns: (extracted_text_dict, detected_format)
        """
        # Load and validate content
        content, detected_format = self.load_content(input_path, format_type)
        format_type = detected_format
        
        # Get appropriate validator
        validator = self.get_validator(format_type)
        
        # Extract translatable text
        extracted_text = validator.extract_text(content)
        
        self.logger.info(f"Extracted {len(extracted_text)} text entries from {format_type} file")
        
        return extracted_text, format_type
    
    def reconstruct_translation(self, 
                              original_content: Any, 
                              translated_text: Dict[str, str], 
                              format_type: str) -> Any:
        """Reconstruct content with translated text"""
        validator = self.get_validator(format_type)
        return validator.reconstruct_content(original_content, translated_text)
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported formats"""
        return list(self.validators.keys())
    
    def is_format_supported(self, format_type: str) -> bool:
        """Check if format is supported"""
        return format_type in self.validators
