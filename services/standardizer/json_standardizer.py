"""
JSON format standardizer
Handles JSON data with translatable string values
"""

import json
from typing import Any, List, Dict, Union
from services.models import Chunk, StandardizedContent, FormatType, StandardizationError
from .base_standardizer import BaseStandardizer


class JsonStandardizer(BaseStandardizer):
    """Standardizer for JSON format with translatable strings"""
    
    def __init__(self, translatable_keys: List[str] = None):
        super().__init__()
        # Default keys that typically contain translatable content
        self.translatable_keys = translatable_keys or [
            'text', 'content', 'message', 'description', 'title', 'label',
            'dialogue', 'speech', 'narrator', 'name', 'subtitle'
        ]
        self.path_separator = '.'
    
    def get_format_type(self) -> FormatType:
        return FormatType.JSON
    
    def validate(self, content: Any) -> bool:
        """Validate if content is valid JSON"""
        if isinstance(content, (dict, list)):
            return True
        
        if isinstance(content, str):
            try:
                json.loads(content)
                return True
            except (json.JSONDecodeError, ValueError):
                return False
        
        return False
    
    def standardize(self, content: Any) -> StandardizedContent:
        """Standardize JSON content"""
        # Parse JSON if it's a string
        if isinstance(content, str):
            try:
                json_data = json.loads(content)
            except (json.JSONDecodeError, ValueError) as e:
                raise StandardizationError(f"Invalid JSON content: {e}")
        else:
            json_data = content
        
        if not self.validate(json_data):
            raise StandardizationError("Content is not valid JSON")
        
        chunks = []
        translatable_paths = []
        
        # Extract translatable content recursively
        self._extract_translatable_content(json_data, "", chunks, translatable_paths)
        
        metadata = {
            'original_type': type(content).__name__,
            'total_chunks': len(chunks),
            'translatable_chunks': len([c for c in chunks if c.is_text]),
            'translatable_paths': translatable_paths,
            'structure_preserved': True
        }
        
        return self.create_standardized_content(chunks, content, metadata)
    
    def _extract_translatable_content(self, 
                                    data: Any, 
                                    current_path: str, 
                                    chunks: List[Chunk],
                                    translatable_paths: List[str]):
        """Recursively extract translatable content from JSON structure"""
        
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{current_path}.{key}" if current_path else key
                
                if self._is_translatable_key(key) and isinstance(value, str) and value.strip():
                    # This is a translatable string
                    chunk = self._create_translatable_chunk(value, new_path, key)
                    chunks.append(chunk)
                    translatable_paths.append(new_path)
                else:
                    # Recurse into nested structures
                    self._extract_translatable_content(value, new_path, chunks, translatable_paths)
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_path = f"{current_path}[{i}]"
                self._extract_translatable_content(item, new_path, chunks, translatable_paths)
        
        elif isinstance(data, str) and data.strip():
            # Standalone string (might be translatable depending on context)
            if self._should_translate_standalone_string(data, current_path):
                chunk = self._create_translatable_chunk(data, current_path, "standalone")
                chunks.append(chunk)
                translatable_paths.append(current_path)
    
    def _is_translatable_key(self, key: str) -> bool:
        """Check if a key typically contains translatable content"""
        key_lower = key.lower()
        return any(translatable_key in key_lower for translatable_key in self.translatable_keys)
    
    def _should_translate_standalone_string(self, text: str, path: str) -> bool:
        """Determine if a standalone string should be translated"""
        # Skip very short strings, UUIDs, URLs, etc.
        if len(text.strip()) < 3:
            return False
        
        # Skip strings that look like IDs, UUIDs, URLs, file paths
        if (text.startswith(('http://', 'https://', 'ftp://', 'file://')) or
            text.count('-') == 4 and len(text) == 36 or  # UUID pattern
            '/' in text and len(text.split('/')) > 2 or  # Path pattern
            text.isdigit() or
            text.replace('-', '').replace('_', '').isalnum() and len(text) > 10):
            return False
        
        return True
    
    def _create_translatable_chunk(self, text: str, path: str, key: str) -> Chunk:
        """Create a chunk for translatable text"""
        metadata = {
            'json_path': path,
            'json_key': key,
            'original_value': text
        }
        
        return Chunk(
            is_text=True,
            original=text,
            standard=text.strip(),
            chunk_type="json_string",
            metadata=metadata
        )
    
    def reconstruct(self, standardized_content: StandardizedContent) -> Any:
        """Reconstruct JSON from standardized content"""
        if standardized_content.format_type != FormatType.JSON:
            raise StandardizationError("Content is not JSON format")
        
        original_content = standardized_content.original_content
        
        # Parse original content if it's a string
        if isinstance(original_content, str):
            try:
                result_data = json.loads(original_content)
            except (json.JSONDecodeError, ValueError) as e:
                raise StandardizationError(f"Cannot parse original JSON: {e}")
        else:
            # Deep copy to avoid modifying original
            result_data = self._deep_copy_json(original_content)
        
        # Apply translations
        for chunk in standardized_content.chunks:
            if chunk.is_text and chunk.translation:
                path = chunk.metadata.get('json_path', '')
                if path:
                    self._set_value_by_path(result_data, path, chunk.translation)
        
        # Return in same format as input
        if isinstance(original_content, str):
            return json.dumps(result_data, ensure_ascii=False, indent=2)
        else:
            return result_data
    
    def _deep_copy_json(self, data: Any) -> Any:
        """Deep copy JSON-serializable data"""
        if isinstance(data, dict):
            return {k: self._deep_copy_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._deep_copy_json(item) for item in data]
        else:
            return data
    
    def _set_value_by_path(self, data: Any, path: str, value: str):
        """Set value in nested JSON structure by path"""
        if not path:
            return
        
        parts = self._parse_path(path)
        current = data
        
        # Navigate to parent of target
        for part in parts[:-1]:
            if isinstance(part, int):
                if isinstance(current, list) and 0 <= part < len(current):
                    current = current[part]
                else:
                    return  # Invalid path
            else:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return  # Invalid path
        
        # Set the final value
        final_part = parts[-1]
        if isinstance(final_part, int):
            if isinstance(current, list) and 0 <= final_part < len(current):
                current[final_part] = value
        else:
            if isinstance(current, dict):
                current[final_part] = value
    
    def _parse_path(self, path: str) -> List[Union[str, int]]:
        """Parse JSON path into components"""
        parts = []
        current_part = ""
        i = 0
        
        while i < len(path):
            if path[i] == '.':
                if current_part:
                    parts.append(current_part)
                    current_part = ""
            elif path[i] == '[':
                if current_part:
                    parts.append(current_part)
                    current_part = ""
                # Find matching ]
                j = i + 1
                while j < len(path) and path[j] != ']':
                    j += 1
                if j < len(path):
                    index_str = path[i+1:j]
                    try:
                        parts.append(int(index_str))
                    except ValueError:
                        parts.append(index_str)  # Non-numeric index
                    i = j
                else:
                    current_part += path[i]  # Malformed, treat as regular char
            else:
                current_part += path[i]
            i += 1
        
        if current_part:
            parts.append(current_part)
        
        return parts
    
    def extract_translatable_content(self, content: Any) -> List[Dict[str, Any]]:
        """Extract translatable content with paths for external processing"""
        standardized = self.standardize(content)
        
        result = []
        for chunk in standardized.chunks:
            if chunk.is_text:
                result.append({
                    'path': chunk.metadata.get('json_path', ''),
                    'key': chunk.metadata.get('json_key', ''),
                    'original': chunk.original,
                    'standard': chunk.standard
                })
        
        return result
    
    def apply_translations(self, content: Any, translations: Dict[str, str]) -> Any:
        """Apply translations using path mapping"""
        standardized = self.standardize(content)
        
        # Apply translations by path
        for chunk in standardized.chunks:
            if chunk.is_text:
                path = chunk.metadata.get('json_path', '')
                if path in translations:
                    chunk.translation = translations[path]
        
        return self.reconstruct(standardized)