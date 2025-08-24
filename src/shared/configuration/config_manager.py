"""
Configuration Manager

Centralized configuration management with support for multiple file formats,
environment variable interpolation, validation, and hot reloading.
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List, Union, Type, get_type_hints
from dataclasses import dataclass, field
from pathlib import Path
import threading
from datetime import datetime

from ..exceptions import ConfigurationException
from .schema_validator import ConfigSchemaValidator
from .environment_loader import EnvironmentVariableLoader
from .file_watcher import ConfigFileWatcher


@dataclass
class ApplicationInfo:
    """Application metadata."""
    name: str = "ai-translation-framework"
    version: str = "2.0.0"
    environment: str = "development"


@dataclass
class TranslationConfig:
    """Translation-specific configuration."""
    batch_size: int = 10
    max_concurrent_jobs: int = 5
    chunk_strategy: str = "semantic"  # semantic, token_based, fixed_size
    context_window_size: int = 5
    quality_threshold: float = 0.8


@dataclass
class ProviderConfig:
    """Provider configuration."""
    type: str
    api_url: Optional[str] = None
    models: Dict[str, str] = field(default_factory=dict)
    rate_limiting: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 30
    retry_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProvidersConfig:
    """Providers configuration."""
    default: str = "openrouter"
    fallback_chain: List[str] = field(default_factory=lambda: ["openrouter", "openai"])
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)


@dataclass
class PerformanceConfig:
    """Performance-related configuration."""
    async_concurrency: int = 10
    connection_pool_size: int = 20
    timeout_seconds: int = 30
    retry_attempts: int = 3
    circuit_breaker: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityConfig:
    """Quality assurance configuration."""
    enable_validation: bool = True
    validation_levels: List[str] = field(default_factory=lambda: ["structure", "content", "consistency"])
    confidence_threshold: float = 0.8
    multi_model_validation: bool = False


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"
    outputs: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MetricsConfig:
    """Metrics configuration."""
    enabled: bool = True
    prometheus_port: int = 9090
    custom_metrics: List[str] = field(default_factory=list)


@dataclass
class TracingConfig:
    """Tracing configuration."""
    enabled: bool = False
    jaeger_endpoint: Optional[str] = None


@dataclass
class ObservabilityConfig:
    """Observability configuration."""
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    tracing: TracingConfig = field(default_factory=TracingConfig)


@dataclass
class ApplicationConfig:
    """Main application configuration."""
    application: ApplicationInfo = field(default_factory=ApplicationInfo)
    translation: TranslationConfig = field(default_factory=TranslationConfig)
    providers: ProvidersConfig = field(default_factory=ProvidersConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)


class ConfigManager:
    """
    Centralized configuration manager with support for multiple formats,
    validation, environment interpolation, and hot reloading.
    """
    
    def __init__(
        self,
        config_paths: Optional[List[str]] = None,
        environment_prefix: str = "TRANSLATION_",
        enable_hot_reload: bool = False
    ):
        self.config_paths = config_paths or []
        self.environment_prefix = environment_prefix
        self.enable_hot_reload = enable_hot_reload
        
        self._config: Optional[ApplicationConfig] = None
        self._raw_config: Dict[str, Any] = {}
        self._lock = threading.RLock()
        
        # Initialize components
        self.schema_validator = ConfigSchemaValidator()
        self.env_loader = EnvironmentVariableLoader(environment_prefix)
        self.file_watcher: Optional[ConfigFileWatcher] = None
        
        # Load initial configuration
        self._load_configuration()
        
        # Setup file watching if enabled
        if enable_hot_reload and self.config_paths:
            self._setup_file_watching()
    
    def get_config(self) -> ApplicationConfig:
        """Get the current configuration."""
        with self._lock:
            if self._config is None:
                raise ConfigurationException(
                    "Configuration not loaded",
                    error_code="CONFIG_NOT_LOADED"
                )
            return self._config
    
    def reload_config(self) -> None:
        """Reload configuration from files."""
        with self._lock:
            self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load configuration from all sources."""
        try:
            # Load from files
            merged_config = {}
            for config_path in self.config_paths:
                file_config = self._load_config_file(config_path)
                merged_config = self._deep_merge(merged_config, file_config)
            
            # Apply environment variable overrides
            merged_config = self.env_loader.apply_environment_overrides(merged_config)
            
            # Validate configuration
            validation_result = self.schema_validator.validate(merged_config)
            if not validation_result.is_valid:
                raise ConfigurationException(
                    f"Configuration validation failed: {', '.join(validation_result.errors)}",
                    error_code="CONFIG_VALIDATION_FAILED",
                    context={"validation_errors": validation_result.errors}
                )
            
            # Store raw config for debugging
            self._raw_config = merged_config
            
            # Convert to typed configuration
            self._config = self._convert_to_typed_config(merged_config)
            
        except Exception as e:
            if isinstance(e, ConfigurationException):
                raise
            raise ConfigurationException(
                f"Failed to load configuration: {str(e)}",
                error_code="CONFIG_LOAD_FAILED",
                inner_exception=e
            )
    
    def _load_config_file(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from a single file."""
        path = Path(config_path)
        
        if not path.exists():
            raise ConfigurationException(
                f"Configuration file not found: {config_path}",
                error_code="CONFIG_FILE_NOT_FOUND",
                context={"file_path": config_path}
            )
        
        try:
            with open(path, 'r', encoding='utf-8') as file:
                if path.suffix.lower() in ['.yml', '.yaml']:
                    return yaml.safe_load(file) or {}
                elif path.suffix.lower() == '.json':
                    return json.load(file) or {}
                else:
                    raise ConfigurationException(
                        f"Unsupported configuration file format: {path.suffix}",
                        error_code="UNSUPPORTED_CONFIG_FORMAT",
                        context={"file_path": config_path, "format": path.suffix}
                    )
        except yaml.YAMLError as e:
            raise ConfigurationException(
                f"Invalid YAML in configuration file {config_path}: {str(e)}",
                error_code="INVALID_YAML",
                context={"file_path": config_path},
                inner_exception=e
            )
        except json.JSONDecodeError as e:
            raise ConfigurationException(
                f"Invalid JSON in configuration file {config_path}: {str(e)}",
                error_code="INVALID_JSON",
                context={"file_path": config_path},
                inner_exception=e
            )
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _convert_to_typed_config(self, config_dict: Dict[str, Any]) -> ApplicationConfig:
        """Convert dictionary to typed configuration object."""
        try:
            # Create configuration with defaults
            app_config = ApplicationConfig()
            
            # Update application info
            if 'application' in config_dict:
                app_info = config_dict['application']
                app_config.application = ApplicationInfo(**app_info)
            
            # Update translation config
            if 'translation' in config_dict:
                trans_config = config_dict['translation']
                app_config.translation = TranslationConfig(**trans_config)
            
            # Update providers config
            if 'providers' in config_dict:
                providers_dict = config_dict['providers']
                providers_config = ProvidersConfig()
                
                if 'default' in providers_dict:
                    providers_config.default = providers_dict['default']
                if 'fallback_chain' in providers_dict:
                    providers_config.fallback_chain = providers_dict['fallback_chain']
                
                # Convert provider configurations
                if 'providers' in providers_dict:
                    for name, provider_dict in providers_dict['providers'].items():
                        providers_config.providers[name] = ProviderConfig(**provider_dict)
                
                app_config.providers = providers_config
            
            # Update performance config
            if 'performance' in config_dict:
                perf_config = config_dict['performance']
                app_config.performance = PerformanceConfig(**perf_config)
            
            # Update quality config
            if 'quality' in config_dict:
                quality_config = config_dict['quality']
                app_config.quality = QualityConfig(**quality_config)
            
            # Update observability config
            if 'observability' in config_dict:
                obs_dict = config_dict['observability']
                obs_config = ObservabilityConfig()
                
                if 'logging' in obs_dict:
                    obs_config.logging = LoggingConfig(**obs_dict['logging'])
                if 'metrics' in obs_dict:
                    obs_config.metrics = MetricsConfig(**obs_dict['metrics'])
                if 'tracing' in obs_dict:
                    obs_config.tracing = TracingConfig(**obs_dict['tracing'])
                
                app_config.observability = obs_config
            
            return app_config
            
        except Exception as e:
            raise ConfigurationException(
                f"Failed to convert configuration to typed object: {str(e)}",
                error_code="CONFIG_CONVERSION_FAILED",
                inner_exception=e
            )
    
    def _setup_file_watching(self) -> None:
        """Setup file watching for hot reload."""
        if not self.config_paths:
            return
        
        self.file_watcher = ConfigFileWatcher(
            file_paths=self.config_paths,
            on_change_callback=self._on_config_file_changed
        )
        self.file_watcher.start_watching()
    
    def _on_config_file_changed(self, file_path: str) -> None:
        """Handle configuration file changes."""
        try:
            self.reload_config()
        except Exception as e:
            # Log error but don't crash the application
            print(f"Error reloading configuration after file change: {e}")
    
    def get_raw_config(self) -> Dict[str, Any]:
        """Get the raw configuration dictionary (for debugging)."""
        with self._lock:
            return self._raw_config.copy()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration."""
        config = self.get_config()
        return {
            "application": {
                "name": config.application.name,
                "version": config.application.version,
                "environment": config.application.environment
            },
            "providers": {
                "default": config.providers.default,
                "available": list(config.providers.providers.keys())
            },
            "performance": {
                "async_concurrency": config.performance.async_concurrency,
                "connection_pool_size": config.performance.connection_pool_size
            },
            "observability": {
                "logging_level": config.observability.logging.level,
                "metrics_enabled": config.observability.metrics.enabled,
                "tracing_enabled": config.observability.tracing.enabled
            }
        }
    
    def stop(self) -> None:
        """Stop file watching and cleanup resources."""
        if self.file_watcher:
            self.file_watcher.stop_watching()