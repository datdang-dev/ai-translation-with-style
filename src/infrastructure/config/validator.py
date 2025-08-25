"""Configuration validation utilities"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import re

from .settings import Settings
from ...core.models import ProvidersConfig, ProviderConfig


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


class ConfigValidator:
    """
    Validates configuration for consistency and correctness.
    
    Performs comprehensive validation beyond basic Pydantic checks,
    including cross-field validation and business logic validation.
    """
    
    def validate_settings(self, settings: Settings) -> None:
        """
        Validate complete settings configuration.
        
        Args:
            settings: Settings object to validate
            
        Raises:
            ConfigValidationError: If validation fails
        """
        errors = []
        
        # Validate basic settings
        errors.extend(self._validate_basic_settings(settings))
        
        # Validate logging configuration
        errors.extend(self._validate_logging_settings(settings))
        
        # Validate translation settings
        errors.extend(self._validate_translation_settings(settings))
        
        # Validate observability settings
        errors.extend(self._validate_observability_settings(settings))
        
        # Validate providers configuration
        if settings.providers:
            errors.extend(self._validate_providers_config(settings.providers))
        
        # Validate cross-component consistency
        errors.extend(self._validate_cross_component_consistency(settings))
        
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(errors)
            raise ConfigValidationError(error_message)
    
    def _validate_basic_settings(self, settings: Settings) -> List[str]:
        """Validate basic application settings"""
        errors = []
        
        # Validate app name
        if not settings.app_name or not settings.app_name.strip():
            errors.append("app_name cannot be empty")
        
        # Validate version format
        version_pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$'
        if not re.match(version_pattern, settings.app_version):
            errors.append(f"app_version '{settings.app_version}' is not a valid semantic version")
        
        # Validate config directory
        if not settings.config_dir.exists():
            errors.append(f"config_dir '{settings.config_dir}' does not exist")
        elif not settings.config_dir.is_dir():
            errors.append(f"config_dir '{settings.config_dir}' is not a directory")
        
        return errors
    
    def _validate_logging_settings(self, settings: Settings) -> List[str]:
        """Validate logging configuration"""
        errors = []
        
        logging = settings.logging
        
        # Validate log file path
        if logging.enable_file_logging and logging.log_file:
            log_dir = logging.log_file.parent
            if not log_dir.exists():
                try:
                    log_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create log directory '{log_dir}': {e}")
        
        # Validate file size limits
        if logging.max_file_size_mb <= 0:
            errors.append("max_file_size_mb must be positive")
        
        if logging.backup_count <= 0:
            errors.append("backup_count must be positive")
        
        # Validate Sentry configuration
        if logging.enable_sentry and not logging.sentry_dsn:
            errors.append("sentry_dsn is required when enable_sentry is True")
        
        return errors
    
    def _validate_translation_settings(self, settings: Settings) -> List[str]:
        """Validate translation configuration"""
        errors = []
        
        translation = settings.translation
        
        # Validate timeout settings
        if translation.default_timeout_seconds <= 0:
            errors.append("default_timeout_seconds must be positive")
        
        if translation.fallback_timeout_seconds <= 0:
            errors.append("fallback_timeout_seconds must be positive")
        
        if translation.fallback_timeout_seconds >= translation.default_timeout_seconds:
            errors.append("fallback_timeout_seconds should be less than default_timeout_seconds")
        
        # Validate concurrency limits
        if translation.max_concurrent_requests <= 0:
            errors.append("max_concurrent_requests must be positive")
        
        if translation.max_batch_size <= 0:
            errors.append("max_batch_size must be positive")
        
        # Validate text length limits
        if translation.min_text_length <= 0:
            errors.append("min_text_length must be positive")
        
        if translation.max_text_length <= translation.min_text_length:
            errors.append("max_text_length must be greater than min_text_length")
        
        # Validate retry settings
        if translation.retry_delay_seconds <= 0:
            errors.append("retry_delay_seconds must be positive")
        
        if translation.retry_exponential_base < 1:
            errors.append("retry_exponential_base must be >= 1")
        
        # Validate rate limiting
        if translation.enable_rate_limiting and translation.default_requests_per_minute <= 0:
            errors.append("default_requests_per_minute must be positive when rate limiting is enabled")
        
        return errors
    
    def _validate_observability_settings(self, settings: Settings) -> List[str]:
        """Validate observability configuration"""
        errors = []
        
        obs = settings.observability
        
        # Validate metrics port
        if obs.enable_metrics:
            if obs.metrics_port < 1024 or obs.metrics_port > 65535:
                errors.append("metrics_port must be between 1024 and 65535")
        
        # Validate tracing configuration
        if obs.enable_tracing and not obs.tracing_endpoint:
            errors.append("tracing_endpoint is required when enable_tracing is True")
        
        if obs.tracing_sample_rate < 0 or obs.tracing_sample_rate > 1:
            errors.append("tracing_sample_rate must be between 0 and 1")
        
        # Validate health check intervals
        if obs.health_check_interval_seconds <= 0:
            errors.append("health_check_interval_seconds must be positive")
        
        if obs.health_check_timeout_seconds <= 0:
            errors.append("health_check_timeout_seconds must be positive")
        
        if obs.health_check_timeout_seconds >= obs.health_check_interval_seconds:
            errors.append("health_check_timeout_seconds should be less than health_check_interval_seconds")
        
        return errors
    
    def _validate_providers_config(self, providers: ProvidersConfig) -> List[str]:
        """Validate providers configuration"""
        errors = []
        
        if not providers.providers:
            errors.append("At least one provider must be configured")
            return errors
        
        provider_names = set()
        
        for provider in providers.providers:
            # Check for duplicate provider names
            if provider.name in provider_names:
                errors.append(f"Duplicate provider name: '{provider.name}'")
            provider_names.add(provider.name)
            
            # Validate individual provider
            errors.extend(self._validate_provider_config(provider))
        
        # Validate default provider
        if providers.default_provider and providers.default_provider not in provider_names:
            errors.append(f"Default provider '{providers.default_provider}' not found in providers list")
        
        # Validate fallback order
        for fallback_provider in providers.fallback_order:
            if fallback_provider not in provider_names:
                errors.append(f"Fallback provider '{fallback_provider}' not found in providers list")
        
        return errors
    
    def _validate_provider_config(self, provider: ProviderConfig) -> List[str]:
        """Validate individual provider configuration"""
        errors = []
        
        # Validate basic fields
        if not provider.name or not provider.name.strip():
            errors.append(f"Provider name cannot be empty")
        
        if not provider.base_url or not provider.base_url.strip():
            errors.append(f"Provider '{provider.name}' base_url cannot be empty")
        
        # Validate URL format
        url_pattern = r'^https?://.+'
        if not re.match(url_pattern, provider.base_url):
            errors.append(f"Provider '{provider.name}' base_url must be a valid HTTP/HTTPS URL")
        
        # Validate API keys
        if provider.auth_type.value == "api_key" and not provider.api_keys:
            errors.append(f"Provider '{provider.name}' requires API keys when using API key authentication")
        
        # Validate models
        if not provider.models:
            errors.append(f"Provider '{provider.name}' must have at least one model configured")
        
        model_names = set()
        for model in provider.models:
            if model.name in model_names:
                errors.append(f"Provider '{provider.name}' has duplicate model name: '{model.name}'")
            model_names.add(model.name)
            
            # Validate model configuration
            if model.max_input_tokens and model.max_input_tokens <= 0:
                errors.append(f"Provider '{provider.name}' model '{model.name}' max_input_tokens must be positive")
            
            if model.max_output_tokens and model.max_output_tokens <= 0:
                errors.append(f"Provider '{provider.name}' model '{model.name}' max_output_tokens must be positive")
        
        # Validate default model
        if provider.default_model and provider.default_model not in model_names:
            errors.append(f"Provider '{provider.name}' default_model '{provider.default_model}' not found in models list")
        
        # Validate rate limits
        rate_limit = provider.rate_limit
        if rate_limit.requests_per_minute <= 0:
            errors.append(f"Provider '{provider.name}' requests_per_minute must be positive")
        
        if rate_limit.backoff_base < 1:
            errors.append(f"Provider '{provider.name}' backoff_base must be >= 1")
        
        # Validate retry configuration
        retry_config = provider.retry_config
        if retry_config.initial_delay_seconds <= 0:
            errors.append(f"Provider '{provider.name}' initial_delay_seconds must be positive")
        
        if retry_config.max_delay_seconds <= retry_config.initial_delay_seconds:
            errors.append(f"Provider '{provider.name}' max_delay_seconds must be greater than initial_delay_seconds")
        
        return errors
    
    def _validate_cross_component_consistency(self, settings: Settings) -> List[str]:
        """Validate consistency between different configuration components"""
        errors = []
        
        # Validate timeout consistency
        if (
            settings.translation.default_timeout_seconds > 0 
            and settings.providers 
            and settings.providers.providers
        ):
            for provider in settings.providers.providers:
                if provider.timeout_seconds > settings.translation.default_timeout_seconds:
                    errors.append(
                        f"Provider '{provider.name}' timeout ({provider.timeout_seconds}s) "
                        f"exceeds default translation timeout ({settings.translation.default_timeout_seconds}s)"
                    )
        
        # Validate concurrency limits
        if settings.providers and settings.providers.providers:
            total_rate_limit = sum(
                provider.rate_limit.requests_per_minute 
                for provider in settings.providers.providers 
                if provider.enabled
            )
            
            if total_rate_limit < settings.translation.max_concurrent_requests:
                errors.append(
                    f"Total provider rate limit ({total_rate_limit} req/min) "
                    f"may be insufficient for max concurrent requests ({settings.translation.max_concurrent_requests})"
                )
        
        return errors
    
    def validate_config_file(self, file_path: Path) -> List[str]:
        """
        Validate a configuration file and return list of errors.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            List of validation error messages (empty if valid)
        """
        try:
            # This would load and validate the config file
            # For now, just check if file exists and is readable
            if not file_path.exists():
                return [f"Configuration file does not exist: {file_path}"]
            
            if not file_path.is_file():
                return [f"Configuration path is not a file: {file_path}"]
            
            # TODO: Add actual file content validation
            return []
            
        except Exception as e:
            return [f"Error validating configuration file: {e}"]