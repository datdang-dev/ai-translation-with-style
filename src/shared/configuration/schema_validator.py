"""
Configuration Schema Validator

Validates configuration dictionaries against defined schemas with detailed error reporting.
"""

from typing import Dict, Any, List, Optional, Union, Type
from dataclasses import dataclass
from enum import Enum


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class ConfigSchemaValidator:
    """
    Validates configuration against predefined schemas.
    
    Provides detailed validation with helpful error messages for configuration issues.
    """
    
    def __init__(self):
        self._schema = self._build_schema()
    
    def validate(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate configuration against schema.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        errors = []
        warnings = []
        
        try:
            # Validate top-level structure
            self._validate_structure(config, self._schema, "", errors, warnings)
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_structure(
        self,
        config: Dict[str, Any],
        schema: Dict[str, Any],
        path: str,
        errors: List[str],
        warnings: List[str]
    ) -> None:
        """Validate configuration structure against schema."""
        
        # Check required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in config:
                errors.append(f"Required field missing: {self._build_path(path, field)}")
        
        # Validate present fields
        for key, value in config.items():
            current_path = self._build_path(path, key)
            
            if key in schema.get('properties', {}):
                field_schema = schema['properties'][key]
                self._validate_field(value, field_schema, current_path, errors, warnings)
            else:
                # Unknown field - warning only
                warnings.append(f"Unknown configuration field: {current_path}")
    
    def _validate_field(
        self,
        value: Any,
        field_schema: Dict[str, Any],
        path: str,
        errors: List[str],
        warnings: List[str]
    ) -> None:
        """Validate a single field against its schema."""
        
        # Type validation
        expected_type = field_schema.get('type')
        if expected_type and not self._check_type(value, expected_type):
            errors.append(f"Invalid type for {path}: expected {expected_type}, got {type(value).__name__}")
            return
        
        # Nested object validation
        if expected_type == 'object' and isinstance(value, dict):
            nested_schema = field_schema.get('properties', {})
            if nested_schema:
                self._validate_structure(value, {'properties': nested_schema, 'required': field_schema.get('required', [])}, path, errors, warnings)
        
        # Array validation
        elif expected_type == 'array' and isinstance(value, list):
            item_schema = field_schema.get('items', {})
            if item_schema:
                for i, item in enumerate(value):
                    item_path = f"{path}[{i}]"
                    self._validate_field(item, item_schema, item_path, errors, warnings)
        
        # String validation
        elif expected_type == 'string' and isinstance(value, str):
            self._validate_string(value, field_schema, path, errors, warnings)
        
        # Number validation
        elif expected_type in ['integer', 'number'] and isinstance(value, (int, float)):
            self._validate_number(value, field_schema, path, errors, warnings)
        
        # Enum validation
        if 'enum' in field_schema:
            if value not in field_schema['enum']:
                errors.append(f"Invalid value for {path}: '{value}' not in allowed values {field_schema['enum']}")
    
    def _validate_string(
        self,
        value: str,
        schema: Dict[str, Any],
        path: str,
        errors: List[str],
        warnings: List[str]
    ) -> None:
        """Validate string field."""
        
        if 'minLength' in schema and len(value) < schema['minLength']:
            errors.append(f"String too short for {path}: minimum length {schema['minLength']}, got {len(value)}")
        
        if 'maxLength' in schema and len(value) > schema['maxLength']:
            errors.append(f"String too long for {path}: maximum length {schema['maxLength']}, got {len(value)}")
        
        if 'pattern' in schema:
            import re
            if not re.match(schema['pattern'], value):
                errors.append(f"String pattern mismatch for {path}: does not match pattern '{schema['pattern']}'")
    
    def _validate_number(
        self,
        value: Union[int, float],
        schema: Dict[str, Any],
        path: str,
        errors: List[str],
        warnings: List[str]
    ) -> None:
        """Validate numeric field."""
        
        if 'minimum' in schema and value < schema['minimum']:
            errors.append(f"Value too small for {path}: minimum {schema['minimum']}, got {value}")
        
        if 'maximum' in schema and value > schema['maximum']:
            errors.append(f"Value too large for {path}: maximum {schema['maximum']}, got {value}")
        
        if 'multipleOf' in schema and value % schema['multipleOf'] != 0:
            errors.append(f"Value for {path} must be multiple of {schema['multipleOf']}, got {value}")
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_mapping = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict,
            'null': type(None)
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type is None:
            return True  # Unknown type, don't validate
        
        return isinstance(value, expected_python_type)
    
    def _build_path(self, parent_path: str, key: str) -> str:
        """Build configuration path for error reporting."""
        if not parent_path:
            return key
        return f"{parent_path}.{key}"
    
    def _build_schema(self) -> Dict[str, Any]:
        """Build the configuration schema."""
        return {
            'type': 'object',
            'properties': {
                'application': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string', 'minLength': 1},
                        'version': {'type': 'string', 'pattern': r'^\d+\.\d+\.\d+'},
                        'environment': {'type': 'string', 'enum': ['development', 'staging', 'production']}
                    },
                    'required': ['name', 'version']
                },
                'translation': {
                    'type': 'object',
                    'properties': {
                        'batch_size': {'type': 'integer', 'minimum': 1, 'maximum': 1000},
                        'max_concurrent_jobs': {'type': 'integer', 'minimum': 1, 'maximum': 100},
                        'chunk_strategy': {'type': 'string', 'enum': ['semantic', 'token_based', 'fixed_size']},
                        'context_window_size': {'type': 'integer', 'minimum': 0, 'maximum': 50},
                        'quality_threshold': {'type': 'number', 'minimum': 0.0, 'maximum': 1.0}
                    }
                },
                'providers': {
                    'type': 'object',
                    'properties': {
                        'default': {'type': 'string', 'minLength': 1},
                        'fallback_chain': {
                            'type': 'array',
                            'items': {'type': 'string', 'minLength': 1}
                        },
                        'providers': {
                            'type': 'object',
                            'additionalProperties': {
                                'type': 'object',
                                'properties': {
                                    'type': {'type': 'string', 'minLength': 1},
                                    'api_url': {'type': 'string'},
                                    'models': {'type': 'object'},
                                    'rate_limiting': {'type': 'object'},
                                    'timeout': {'type': 'integer', 'minimum': 1, 'maximum': 300},
                                    'retry_config': {'type': 'object'}
                                },
                                'required': ['type']
                            }
                        }
                    },
                    'required': ['default']
                },
                'performance': {
                    'type': 'object',
                    'properties': {
                        'async_concurrency': {'type': 'integer', 'minimum': 1, 'maximum': 1000},
                        'connection_pool_size': {'type': 'integer', 'minimum': 1, 'maximum': 1000},
                        'timeout_seconds': {'type': 'integer', 'minimum': 1, 'maximum': 600},
                        'retry_attempts': {'type': 'integer', 'minimum': 0, 'maximum': 10},
                        'circuit_breaker': {'type': 'object'}
                    }
                },
                'quality': {
                    'type': 'object',
                    'properties': {
                        'enable_validation': {'type': 'boolean'},
                        'validation_levels': {
                            'type': 'array',
                            'items': {'type': 'string', 'enum': ['structure', 'content', 'consistency', 'quality']}
                        },
                        'confidence_threshold': {'type': 'number', 'minimum': 0.0, 'maximum': 1.0},
                        'multi_model_validation': {'type': 'boolean'}
                    }
                },
                'observability': {
                    'type': 'object',
                    'properties': {
                        'logging': {
                            'type': 'object',
                            'properties': {
                                'level': {'type': 'string', 'enum': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']},
                                'format': {'type': 'string', 'enum': ['json', 'text']},
                                'outputs': {'type': 'array', 'items': {'type': 'object'}}
                            }
                        },
                        'metrics': {
                            'type': 'object',
                            'properties': {
                                'enabled': {'type': 'boolean'},
                                'prometheus_port': {'type': 'integer', 'minimum': 1024, 'maximum': 65535},
                                'custom_metrics': {'type': 'array', 'items': {'type': 'string'}}
                            }
                        },
                        'tracing': {
                            'type': 'object',
                            'properties': {
                                'enabled': {'type': 'boolean'},
                                'jaeger_endpoint': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }