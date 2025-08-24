"""
Environment Variable Loader

Handles loading and interpolation of environment variables in configuration files.
Supports default values, type conversion, and secure handling of sensitive data.
"""

import os
import re
from typing import Dict, Any, Optional, Union, Pattern
from ..exceptions import ConfigurationException


class EnvironmentVariableLoader:
    """
    Loads and interpolates environment variables in configuration.
    
    Supports patterns like:
    - ${VAR_NAME} - Required variable
    - ${VAR_NAME:default} - Variable with default value
    - ${VAR_NAME:} - Variable with empty string default
    """
    
    # Pattern to match environment variable references
    ENV_VAR_PATTERN: Pattern = re.compile(r'\$\{([^}]+)\}')
    
    def __init__(self, prefix: str = ""):
        """
        Initialize the environment loader.
        
        Args:
            prefix: Optional prefix for environment variables (e.g., "TRANSLATION_")
        """
        self.prefix = prefix
        self._sensitive_keys = {'password', 'token', 'key', 'secret', 'credential'}
    
    def apply_environment_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with environment variables interpolated
        """
        return self._process_value(config)
    
    def _process_value(self, value: Any) -> Any:
        """Process a value, handling environment variable interpolation."""
        if isinstance(value, str):
            return self._interpolate_string(value)
        elif isinstance(value, dict):
            return {k: self._process_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._process_value(item) for item in value]
        else:
            return value
    
    def _interpolate_string(self, text: str) -> Union[str, int, float, bool]:
        """
        Interpolate environment variables in a string.
        
        Args:
            text: String that may contain environment variable references
            
        Returns:
            String with environment variables resolved, or converted type
        """
        def replace_var(match):
            var_spec = match.group(1)
            return self._resolve_variable(var_spec)
        
        # Replace all environment variable references
        result = self.ENV_VAR_PATTERN.sub(replace_var, text)
        
        # If the entire string was a single environment variable, try type conversion
        if text.startswith('${') and text.endswith('}') and not self.ENV_VAR_PATTERN.search(result):
            return self._convert_type(result)
        
        return result
    
    def _resolve_variable(self, var_spec: str) -> str:
        """
        Resolve a single environment variable specification.
        
        Args:
            var_spec: Variable specification (e.g., "VAR_NAME:default")
            
        Returns:
            Resolved variable value
        """
        # Parse variable name and default value
        if ':' in var_spec:
            var_name, default_value = var_spec.split(':', 1)
        else:
            var_name = var_spec
            default_value = None
        
        var_name = var_name.strip()
        
        # Add prefix if configured
        full_var_name = f"{self.prefix}{var_name}" if self.prefix else var_name
        
        # Get environment variable value
        env_value = os.environ.get(full_var_name)
        
        if env_value is not None:
            return env_value
        elif default_value is not None:
            return default_value
        else:
            raise ConfigurationException(
                f"Required environment variable '{full_var_name}' is not set",
                error_code="REQUIRED_ENV_VAR_MISSING",
                context={"variable_name": full_var_name, "original_spec": var_spec}
            )
    
    def _convert_type(self, value: str) -> Union[str, int, float, bool]:
        """
        Convert string value to appropriate type.
        
        Args:
            value: String value to convert
            
        Returns:
            Value converted to appropriate type
        """
        if not value:
            return value
        
        # Try boolean conversion
        lower_value = value.lower()
        if lower_value in ('true', 'yes', '1', 'on'):
            return True
        elif lower_value in ('false', 'no', '0', 'off'):
            return False
        
        # Try integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def get_environment_info(self) -> Dict[str, Any]:
        """
        Get information about environment variables used in configuration.
        
        Returns:
            Dictionary with environment variable information
        """
        env_vars = {}
        prefix_len = len(self.prefix) if self.prefix else 0
        
        for key, value in os.environ.items():
            if self.prefix and key.startswith(self.prefix):
                clean_key = key[prefix_len:]
                env_vars[clean_key] = self._mask_sensitive_value(clean_key, value)
            elif not self.prefix:
                env_vars[key] = self._mask_sensitive_value(key, value)
        
        return {
            "prefix": self.prefix,
            "variables": env_vars,
            "total_count": len(env_vars)
        }
    
    def _mask_sensitive_value(self, key: str, value: str) -> str:
        """
        Mask sensitive values for logging/debugging.
        
        Args:
            key: Environment variable key
            value: Environment variable value
            
        Returns:
            Masked value if sensitive, otherwise original value
        """
        key_lower = key.lower()
        if any(sensitive_key in key_lower for sensitive_key in self._sensitive_keys):
            if len(value) <= 4:
                return '*' * len(value)
            else:
                return value[:2] + '*' * (len(value) - 4) + value[-2:]
        return value
    
    def validate_required_variables(self, required_vars: list[str]) -> Dict[str, bool]:
        """
        Validate that required environment variables are set.
        
        Args:
            required_vars: List of required variable names (without prefix)
            
        Returns:
            Dictionary mapping variable names to whether they are set
        """
        results = {}
        for var_name in required_vars:
            full_var_name = f"{self.prefix}{var_name}" if self.prefix else var_name
            results[var_name] = full_var_name in os.environ
        
        return results
    
    def set_variable(self, name: str, value: str, use_prefix: bool = True) -> None:
        """
        Set an environment variable (useful for testing).
        
        Args:
            name: Variable name
            value: Variable value
            use_prefix: Whether to add the configured prefix
        """
        full_name = f"{self.prefix}{name}" if use_prefix and self.prefix else name
        os.environ[full_name] = value
    
    def unset_variable(self, name: str, use_prefix: bool = True) -> None:
        """
        Unset an environment variable (useful for testing).
        
        Args:
            name: Variable name
            use_prefix: Whether to add the configured prefix
        """
        full_name = f"{self.prefix}{name}" if use_prefix and self.prefix else name
        if full_name in os.environ:
            del os.environ[full_name]