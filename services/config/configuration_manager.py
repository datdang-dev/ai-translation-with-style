"""
Configuration manager for centralized configuration handling
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from services.models import (
    ProviderConfig, ResiliencyConfig, CacheConfig, 
    TranslationError
)
from services.common.logger import get_logger


class ConfigurationManager:
    """Centralized configuration management with environment variable support"""
    
    def __init__(self, config_path: str = None, env_prefix: str = "TRANSLATION_"):
        self.config_path = config_path or "config/translation.yaml"
        self.env_prefix = env_prefix
        self.logger = get_logger("ConfigurationManager")
        
        # Configuration data
        self._config_data: Dict[str, Any] = {}
        self._env_overrides: Dict[str, Any] = {}
        
        # Load configuration
        self._load_configuration()
        self._load_environment_overrides()
    
    def _load_configuration(self):
        """Load configuration from file"""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            self.logger.warning(f"Configuration file not found: {self.config_path}, using defaults")
            self._config_data = self._get_default_config()
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.suffix.lower() in ['.yaml', '.yml']:
                    self._config_data = yaml.safe_load(f) or {}
                elif config_file.suffix.lower() == '.json':
                    self._config_data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {config_file.suffix}")
            
            self.logger.info(f"Configuration loaded from {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.logger.info("Using default configuration")
            self._config_data = self._get_default_config()
    
    def _load_environment_overrides(self):
        """Load configuration overrides from environment variables"""
        env_overrides = {}
        
        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                # Convert environment variable to config key
                config_key = key[len(self.env_prefix):].lower().replace('_', '.')
                
                # Try to parse as JSON, fallback to string
                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    parsed_value = value
                
                self._set_nested_value(env_overrides, config_key, parsed_value)
        
        self._env_overrides = env_overrides
        
        if env_overrides:
            self.logger.info(f"Loaded {len(env_overrides)} environment overrides")
    
    def _set_nested_value(self, data: Dict[str, Any], key_path: str, value: Any):
        """Set value in nested dictionary using dot notation"""
        keys = key_path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _get_nested_value(self, data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
        """Get value from nested dictionary using dot notation"""
        keys = key_path.split('.')
        current = data
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value with environment override support"""
        # Check environment overrides first
        env_value = self._get_nested_value(self._env_overrides, key)
        if env_value is not None:
            return env_value
        
        # Check configuration file
        config_value = self._get_nested_value(self._config_data, key)
        if config_value is not None:
            return config_value
        
        return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        # Get from config file
        config_section = self._get_nested_value(self._config_data, section, {})
        
        # Apply environment overrides
        env_section = self._get_nested_value(self._env_overrides, section, {})
        
        # Merge configurations (env overrides config)
        merged = dict(config_section)
        self._deep_merge(merged, env_section)
        
        return merged
    
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Deep merge source into target"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def reload_config(self):
        """Reload configuration from file"""
        self.logger.info("Reloading configuration")
        self._load_configuration()
        self._load_environment_overrides()
    
    def validate_config(self) -> bool:
        """Validate current configuration"""
        try:
            # Validate required sections exist
            required_sections = ['providers', 'resiliency', 'cache']
            for section in required_sections:
                if not self.get_section(section):
                    self.logger.warning(f"Missing required configuration section: {section}")
            
            # Validate provider configurations
            providers = self.get_provider_configs()
            if not providers:
                self.logger.warning("No providers configured")
            
            # Validate at least one provider is enabled
            enabled_providers = [p for p in providers.values() if p.enabled]
            if not enabled_providers:
                self.logger.error("No providers are enabled")
                return False
            
            self.logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
    
    def get_provider_configs(self) -> Dict[str, ProviderConfig]:
        """Get provider configurations"""
        providers_config = self.get_section('providers')
        provider_configs = {}
        
        for name, config in providers_config.items():
            if isinstance(config, dict):
                provider_configs[name] = ProviderConfig(
                    name=name,
                    enabled=config.get('enabled', True),
                    priority=config.get('priority', 1),
                    max_requests_per_minute=config.get('max_requests_per_minute', 20),
                    timeout=config.get('timeout', 30.0),
                    config=config.get('config', {})
                )
        
        return provider_configs
    
    def get_resiliency_config(self) -> ResiliencyConfig:
        """Get resiliency configuration"""
        resiliency = self.get_section('resiliency')
        
        return ResiliencyConfig(
            max_retries=resiliency.get('max_retries', 3),
            retry_delay=resiliency.get('retry_delay', 1.0),
            retry_backoff_multiplier=resiliency.get('retry_backoff_multiplier', 2.0),
            circuit_breaker_threshold=resiliency.get('circuit_breaker_threshold', 5),
            circuit_breaker_timeout=resiliency.get('circuit_breaker_timeout', 60.0),
            request_timeout=resiliency.get('request_timeout', 30.0)
        )
    
    def get_cache_config(self) -> CacheConfig:
        """Get cache configuration"""
        cache = self.get_section('cache')
        
        return CacheConfig(
            enabled=cache.get('enabled', True),
            ttl_seconds=cache.get('ttl_seconds', 3600),
            max_size=cache.get('max_size', 1000),
            backend=cache.get('backend', 'memory'),
            redis_url=cache.get('redis_url')
        )
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.get_section('logging')
    
    def get_api_keys(self) -> Dict[str, str]:
        """Get API keys from configuration"""
        # Try to get from dedicated API keys file first
        api_keys_file = Path("config/api_keys.json")
        if api_keys_file.exists():
            try:
                with open(api_keys_file, 'r', encoding='utf-8') as f:
                    api_keys_data = json.load(f)
                    return api_keys_data.get('api_keys', {})
            except Exception as e:
                self.logger.warning(f"Failed to load API keys file: {e}")
        
        # Fallback to main configuration
        return self.get_section('api_keys')
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'providers': {
                'openrouter': {
                    'enabled': True,
                    'priority': 1,
                    'max_requests_per_minute': 20,
                    'timeout': 30.0,
                    'config': {
                        'model': 'anthropic/claude-3.5-sonnet',
                        'max_tokens': 4000,
                        'temperature': 0.3
                    }
                },
                'google_translate': {
                    'enabled': False,
                    'priority': 2,
                    'max_requests_per_minute': 100,
                    'timeout': 10.0,
                    'config': {}
                }
            },
            'resiliency': {
                'max_retries': 3,
                'retry_delay': 1.0,
                'retry_backoff_multiplier': 2.0,
                'circuit_breaker_threshold': 5,
                'circuit_breaker_timeout': 60.0,
                'request_timeout': 30.0
            },
            'cache': {
                'enabled': True,
                'ttl_seconds': 3600,
                'max_size': 1000,
                'backend': 'memory'
            },
            'processing': {
                'batch_size': 10,
                'max_concurrent': 3,
                'job_delay': 0.1
            },
            'logging': {
                'level': 'INFO',
                'format': 'structured',
                'file': 'logs/translation.log'
            }
        }
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration"""
        return self.get_section('processing')
    
    def set_config(self, key: str, value: Any):
        """Set configuration value (runtime only)"""
        self._set_nested_value(self._config_data, key, value)
        self.logger.info(f"Configuration updated: {key} = {value}")
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get complete configuration with environment overrides applied"""
        merged_config = dict(self._config_data)
        self._deep_merge(merged_config, self._env_overrides)
        return merged_config
    
    def export_config(self, output_path: str = None, format: str = 'yaml'):
        """Export current configuration to file"""
        if output_path is None:
            output_path = f"config/exported_config.{format}"
        
        config_data = self.get_all_config()
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if format.lower() == 'yaml':
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                elif format.lower() == 'json':
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                else:
                    raise ValueError(f"Unsupported format: {format}")
            
            self.logger.info(f"Configuration exported to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to export configuration: {e}")
            raise
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging"""
        return {
            'config_file': self.config_path,
            'config_file_exists': Path(self.config_path).exists(),
            'env_prefix': self.env_prefix,
            'env_overrides_count': len(self._env_overrides),
            'providers_configured': len(self.get_provider_configs()),
            'cache_enabled': self.get_cache_config().enabled,
            'validation_passed': self.validate_config()
        }
