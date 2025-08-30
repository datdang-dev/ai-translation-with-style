"""
Configuration Manager
Handles YAML configuration loading and validation
"""

import yaml
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from services.common.logger import get_logger

class ConfigManager:
    """Manages application configuration from YAML files"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.logger = get_logger("ConfigManager")
        self.config: Dict[str, Any] = {}
        self.prompts: Dict[str, Any] = {}
        self._load_config()
        self._load_prompts()
    
    def _load_config(self) -> None:
        """Load main configuration from YAML file"""
        try:
            if not os.path.exists(self.config_path):
                self.logger.warning(f"Config file not found: {self.config_path}")
                self.config = self._get_default_config()
                return
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            self.logger.info(f"Configuration loaded from: {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.config = self._get_default_config()
    
    def _load_prompts(self) -> None:
        """Load prompts from JSON file"""
        try:
            prompts_path = "config/prompts.json"
            if os.path.exists(prompts_path):
                with open(prompts_path, 'r', encoding='utf-8') as f:
                    self.prompts = json.load(f)
                self.logger.info(f"Prompts loaded from: {prompts_path}")
            else:
                self.logger.warning(f"Prompts file not found: {prompts_path}")
                self.prompts = {}
        except Exception as e:
            self.logger.error(f"Failed to load prompts: {e}")
            self.prompts = {}
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if loading fails"""
        return {
            "api": {
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "max_retries": 3,
                "backoff_base": 2.0,
                "max_requests_per_minute": 20
            },
            "translation": {
                "model": "google/gemini-2.0-flash-exp:free",
                "temperature": 1,
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0,
                "top_p": 1,
                "top_k": 50,
                "min_p": 0,
                "top_a": 1,
                "repetition_penalty": 1.2
            },
            "scheduling": {
                "job_delay": 10.0,
                "max_concurrent": 100
            },
            "validation": {
                "strict_json": True,
                "allow_partial": False
            },
            "standardization": {
                "default_format": "json",
                "auto_convert": True
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key (e.g., 'api.url')"""
        try:
            keys = key.split('.')
            value = self.config
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_prompt(self, key: str, default: str = "") -> str:
        """Get prompt value by key"""
        return self.prompts.get(key, default)
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration section"""
        return self.config.get("api", {})
    
    def get_translation_config(self) -> Dict[str, Any]:
        """Get translation configuration section"""
        return self.config.get("translation", {})
    
    def get_scheduling_config(self) -> Dict[str, Any]:
        """Get scheduling configuration section"""
        return self.config.get("scheduling", {})
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation configuration section"""
        return self.config.get("validation", {})
    
    def get_standardization_config(self) -> Dict[str, Any]:
        """Get standardization configuration section"""
        return self.config.get("standardization", {})
    
    def reload(self) -> None:
        """Reload configuration from files"""
        self._load_config()
        self._load_prompts()
        self.logger.info("Configuration reloaded")