"""
Preset loader for managing translation prompt presets
"""

import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from services.common.logger import get_logger


class PresetLoader:
    """Loader for translation preset configurations"""
    
    def __init__(self, preset_dir: str = "config"):
        self.preset_dir = Path(preset_dir)
        self.logger = get_logger("PresetLoader")
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def load_preset(self, preset_name: str) -> Dict[str, Any]:
        """Load a specific preset configuration
        
        Args:
            preset_name: Name of the preset (without .json extension)
            
        Returns:
            Dictionary containing preset configuration
        """
        if preset_name in self._cache:
            return self._cache[preset_name]
        
        preset_path = self.preset_dir / f"{preset_name}.json"
        
        if not preset_path.exists():
            self.logger.warning(f"Preset file not found: {preset_path}")
            return self._get_default_preset()
        
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                preset_data = json.load(f)
            
            # Validate preset structure
            validated_preset = self._validate_preset(preset_data, preset_name)
            
            # Cache the preset
            self._cache[preset_name] = validated_preset
            
            self.logger.info(f"Loaded preset: {preset_name}")
            return validated_preset
            
        except Exception as e:
            self.logger.error(f"Failed to load preset {preset_name}: {e}")
            return self._get_default_preset()
    
    def _validate_preset(self, preset_data: Dict[str, Any], preset_name: str) -> Dict[str, Any]:
        """Validate and normalize preset configuration"""
        validated = {}
        
        # Model configuration
        validated['model'] = preset_data.get('model', 'google/gemini-2.0-flash-exp:free')
        validated['tokenizer_name'] = preset_data.get('tokenizer_name', '')
        
        # Messages for prompt
        messages = preset_data.get('messages', [])
        if not isinstance(messages, list):
            self.logger.warning(f"Preset {preset_name}: 'messages' should be a list, using default")
            messages = []
        validated['messages'] = messages
        
        # Generation parameters
        validated['temperature'] = float(preset_data.get('temperature', 0.7))
        validated['presence_penalty'] = float(preset_data.get('presence_penalty', 0.0))
        validated['frequency_penalty'] = float(preset_data.get('frequency_penalty', 0.0))
        validated['top_p'] = float(preset_data.get('top_p', 1.0))
        validated['top_k'] = int(preset_data.get('top_k', 50))
        validated['min_p'] = float(preset_data.get('min_p', 0.0))
        validated['top_a'] = float(preset_data.get('top_a', 1.0))
        validated['repetition_penalty'] = float(preset_data.get('repetition_penalty', 1.0))
        
        # Optional max_tokens
        if 'max_tokens' in preset_data:
            validated['max_tokens'] = int(preset_data['max_tokens'])
        
        self.logger.debug(f"Validated preset {preset_name} with model: {validated['model']}")
        return validated
    
    def _get_default_preset(self) -> Dict[str, Any]:
        """Get default preset configuration"""
        return {
            'model': 'google/gemini-2.0-flash-exp:free',
            'tokenizer_name': '',
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a professional translator. Translate the given text accurately while preserving the original meaning and tone.'
                }
            ],
            'temperature': 0.7,
            'presence_penalty': 0.0,
            'frequency_penalty': 0.0,
            'top_p': 1.0,
            'top_k': 50,
            'min_p': 0.0,
            'top_a': 1.0,
            'repetition_penalty': 1.0
        }
    
    def list_available_presets(self) -> List[str]:
        """List all available preset files"""
        if not self.preset_dir.exists():
            return []
        
        preset_files = []
        for file_path in self.preset_dir.glob("*.json"):
            # Skip non-preset JSON files
            if file_path.name not in ['api_keys.json']:
                preset_files.append(file_path.stem)
        
        return sorted(preset_files)
    
    def reload_preset(self, preset_name: str) -> Dict[str, Any]:
        """Reload a preset from disk (bypassing cache)"""
        if preset_name in self._cache:
            del self._cache[preset_name]
        return self.load_preset(preset_name)
    
    def clear_cache(self):
        """Clear all cached presets"""
        self._cache.clear()
        self.logger.info("Preset cache cleared")
    
    def get_preset_info(self, preset_name: str) -> Dict[str, Any]:
        """Get information about a preset without loading it fully"""
        preset_path = self.preset_dir / f"{preset_name}.json"
        
        if not preset_path.exists():
            return {'exists': False}
        
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                preset_data = json.load(f)
            
            return {
                'exists': True,
                'model': preset_data.get('model', 'unknown'),
                'message_count': len(preset_data.get('messages', [])),
                'temperature': preset_data.get('temperature', 0.7),
                'file_size': preset_path.stat().st_size,
                'last_modified': preset_path.stat().st_mtime
            }
            
        except Exception as e:
            return {
                'exists': True,
                'error': str(e)
            }