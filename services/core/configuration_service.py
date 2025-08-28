"""
Configuration service for centralized config management.
"""

import json
import os
from typing import Dict, Any
from pathlib import Path

from .interfaces import IConfigurationService, Result
from .exceptions import ConfigurationError


class ConfigurationService(IConfigurationService):
    """Centralized configuration management service"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file"""
        try:
            if not os.path.exists(self.config_path):
                raise ConfigurationError(f"Configuration file not found: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
                
            # Load API keys from separate file if configured
            api_keys_path = self._config.get("api_keys_file", "config/api_keys.json")
            if os.path.exists(api_keys_path):
                with open(api_keys_path, 'r', encoding='utf-8') as f:
                    api_keys_config = json.load(f)
                    self._config["api_keys"] = api_keys_config.get("api_keys", [])
                    
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise ConfigurationError(f"Failed to load configuration: {str(e)}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        return self._config.get(section, {})
    
    def reload(self) -> Result:
        """Reload configuration from file"""
        try:
            self._load_config()
            return Result.ok()
        except ConfigurationError as e:
            return Result.error(1001, str(e))
    
    def get_api_keys(self) -> list:
        """Get API keys list"""
        return self._config.get("api_keys", [])
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration"""
        return {
            "api_url": self.get("api_url", "https://openrouter.ai/api/v1/chat/completions"),
            "max_retries": self.get("max_retries", 3),
            "backoff_base": self.get("backoff_base", 2.0),
            "max_requests_per_minute": self.get("max_requests_per_minute", 20),
            "timeout": self.get("timeout", 30)
        }
    
    def get_batch_config(self) -> Dict[str, Any]:
        """Get batch processing configuration"""
        return {
            "max_concurrent": self.get("batch.max_concurrent", 3),
            "job_delay": self.get("batch.job_delay", 10.0),
            "queue_size": self.get("batch.queue_size", 1000)
        }