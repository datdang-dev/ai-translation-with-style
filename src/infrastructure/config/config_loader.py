"""Configuration loader with support for YAML, JSON, and environment variables"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import yaml
from pydantic import ValidationError

from .settings import Settings
from .validator import ConfigValidator
from ...core.models import ProvidersConfig


class ConfigLoadError(Exception):
    """Raised when configuration loading fails"""
    pass


class ConfigLoader:
    """
    Loads and validates configuration from multiple sources.
    
    Supports loading from:
    1. Environment variables
    2. YAML configuration files
    3. JSON configuration files
    4. Default values
    
    Configuration is merged with the following precedence (highest to lowest):
    1. Environment variables
    2. Explicit config file
    3. Environment-specific config file (e.g., production.yaml)
    4. Default config file (default.yaml)
    5. Built-in defaults
    """
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        """
        Initialize configuration loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self.validator = ConfigValidator()
    
    def load_settings(
        self, 
        config_file: Optional[str] = None,
        environment: Optional[str] = None
    ) -> Settings:
        """
        Load complete application settings.
        
        Args:
            config_file: Specific config file to load
            environment: Environment name for env-specific config
            
        Returns:
            Validated Settings object
            
        Raises:
            ConfigLoadError: If configuration loading or validation fails
        """
        try:
            # Start with base settings from environment variables
            settings = Settings()
            
            # Load configuration files
            config_data = self._load_config_files(config_file, environment)
            
            # Merge with settings
            if config_data:
                # Update settings with config file data
                for key, value in config_data.items():
                    if hasattr(settings, key):
                        if isinstance(getattr(settings, key), BaseSettings):
                            # Handle nested settings objects
                            nested_settings = getattr(settings, key)
                            if isinstance(value, dict):
                                for nested_key, nested_value in value.items():
                                    if hasattr(nested_settings, nested_key):
                                        setattr(nested_settings, nested_key, nested_value)
                        else:
                            setattr(settings, key, value)
            
            # Load providers configuration separately
            providers_config = self._load_providers_config(settings)
            if providers_config:
                settings.providers = providers_config
            
            # Validate final configuration
            self.validator.validate_settings(settings)
            
            return settings
            
        except ValidationError as e:
            raise ConfigLoadError(f"Configuration validation failed: {e}")
        except Exception as e:
            raise ConfigLoadError(f"Failed to load configuration: {e}")
    
    def _load_config_files(
        self, 
        explicit_file: Optional[str] = None,
        environment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Load configuration from files with proper precedence"""
        config_data = {}
        
        # Load default configuration
        default_file = self.config_dir / "default.yaml"
        if default_file.exists():
            default_config = self._load_file(default_file)
            config_data.update(default_config)
        
        # Load environment-specific configuration
        if environment:
            env_file = self.config_dir / f"{environment}.yaml"
            if env_file.exists():
                env_config = self._load_file(env_file)
                config_data = self._deep_merge(config_data, env_config)
        
        # Load explicit configuration file
        if explicit_file:
            explicit_path = self.config_dir / explicit_file
            if explicit_path.exists():
                explicit_config = self._load_file(explicit_path)
                config_data = self._deep_merge(config_data, explicit_config)
            else:
                raise ConfigLoadError(f"Explicit config file not found: {explicit_path}")
        
        return config_data
    
    def _load_providers_config(self, settings: Settings) -> Optional[ProvidersConfig]:
        """Load providers configuration"""
        providers_file = settings.providers_config_path
        
        if not providers_file.exists():
            # Create a minimal providers config file if it doesn't exist
            self._create_default_providers_config(providers_file)
            return None
        
        try:
            providers_data = self._load_file(providers_file)
            return ProvidersConfig(**providers_data)
        except Exception as e:
            raise ConfigLoadError(f"Failed to load providers config: {e}")
    
    def _load_file(self, file_path: Path) -> Dict[str, Any]:
        """Load a single configuration file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yml', '.yaml']:
                    return yaml.safe_load(f) or {}
                elif file_path.suffix.lower() == '.json':
                    return json.load(f) or {}
                else:
                    raise ConfigLoadError(f"Unsupported file format: {file_path.suffix}")
        except FileNotFoundError:
            return {}
        except yaml.YAMLError as e:
            raise ConfigLoadError(f"Invalid YAML in {file_path}: {e}")
        except json.JSONDecodeError as e:
            raise ConfigLoadError(f"Invalid JSON in {file_path}: {e}")
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if (
                key in result 
                and isinstance(result[key], dict) 
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _create_default_providers_config(self, file_path: Path) -> None:
        """Create a default providers configuration file"""
        default_config = {
            "providers": [],
            "default_provider": None,
            "enable_fallback": True,
            "fallback_order": []
        }
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, indent=2)
        except Exception as e:
            raise ConfigLoadError(f"Failed to create default providers config: {e}")
    
    def save_config(self, settings: Settings, file_path: Optional[Path] = None) -> None:
        """
        Save current settings to a configuration file.
        
        Args:
            settings: Settings object to save
            file_path: Optional path to save to (defaults to config_dir/current.yaml)
        """
        if file_path is None:
            file_path = self.config_dir / "current.yaml"
        
        try:
            # Convert settings to dict, excluding providers
            config_dict = settings.dict(exclude={'providers'})
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                
        except Exception as e:
            raise ConfigLoadError(f"Failed to save configuration: {e}")
    
    def validate_config_file(self, file_path: Path) -> bool:
        """
        Validate a configuration file without loading it into settings.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            config_data = self._load_file(file_path)
            # Basic validation - check if it's a valid dict
            return isinstance(config_data, dict)
        except Exception:
            return False
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for configuration validation.
        
        Returns:
            JSON schema dictionary
        """
        return Settings.schema()