"""
Configuration loader for the translation service
Handles loading configuration from files with proper error handling and logging
"""

import json
import os
from typing import Dict, Any, Optional
from services.common.logger import get_logger


class ConfigurationLoader:
    """Handles loading configuration from files with proper error handling and logging"""
    
    def __init__(self, config_path: str = "config/preset_translation.json"):
        """
        Initialize ConfigurationLoader
        
        :param config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.logger = get_logger("ConfigurationLoader")
        self.config = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file with error handling"""
        try:
            # Check if file exists
            if not os.path.exists(self.config_path):
                self.logger.error(f"Configuration file not found: {self.config_path}")
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            # Load JSON configuration
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            self.logger.info(f"Successfully loaded configuration from {self.config_path}")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file {self.config_path}: {e}")
            raise ValueError(f"Invalid JSON in configuration file {self.config_path}: {e}")
        
        except PermissionError as e:
            self.logger.error(f"Permission denied when reading configuration file {self.config_path}: {e}")
            raise PermissionError(f"Permission denied when reading configuration file {self.config_path}: {e}")
        
        except FileNotFoundError as e:
            self.logger.error(f"Configuration file not found: {self.config_path}")
            raise e
        
        except Exception as e:
            self.logger.error(f"Unexpected error loading configuration from {self.config_path}: {e}")
            raise Exception(f"Unexpected error loading configuration from {self.config_path}: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the loaded configuration
        
        :return: Configuration dictionary
        """
        return self.config.copy()
    
    def get_value(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a specific configuration value by key
        
        :param key: Configuration key
        :param default: Default value if key not found
        :return: Configuration value or default
        """
        return self.config.get(key, default)
    
    def get_nested_value(self, keys: str, default: Optional[Any] = None) -> Any:
        """
        Get a nested configuration value using dot notation
        
        :param keys: Dot-separated keys (e.g., "messages.0.role")
        :param default: Default value if key not found
        :return: Configuration value or default
        """
        try:
            keys_list = keys.split('.')
            value = self.config
            
            for key in keys_list:
                # Handle array indexing
                if key.isdigit():
                    key = int(key)
                value = value[key]
            
            return value
        except (KeyError, IndexError, TypeError):
            return default
    
    def reload_config(self) -> None:
        """
        Reload configuration from file
        """
        self.logger.info("Reloading configuration...")
        self._load_config()
    
    def update_config_path(self, new_path: str) -> None:
        """
        Update the configuration file path and reload
        
        :param new_path: New configuration file path
        """
        self.config_path = new_path
        self.logger.info(f"Updated configuration path to {new_path}")
        self.reload_config()


# Convenience function for easy access
def load_config(config_path: str = "config/preset_translation.json") -> Dict[str, Any]:
    """
    Convenience function to load configuration
    
    :param config_path: Path to the configuration file
    :return: Configuration dictionary
    """
    loader = ConfigurationLoader(config_path)
    return loader.get_config()