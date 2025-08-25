"""Application settings with Pydantic validation"""

from typing import Dict, List, Optional, Any, Union
from pathlib import Path
try:
    from pydantic.v1 import BaseSettings, Field, validator
except ImportError:
    from pydantic import BaseSettings, Field, validator
from enum import Enum

from ...core.models import ProvidersConfig


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Log output formats"""
    JSON = "json"
    TEXT = "text"
    COLORED = "colored"


class Environment(str, Enum):
    """Application environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LoggingSettings(BaseSettings):
    """Logging configuration"""
    
    level: LogLevel = Field(default=LogLevel.INFO)
    format: LogFormat = Field(default=LogFormat.JSON)
    
    # File logging
    enable_file_logging: bool = Field(default=True)
    log_file: Optional[Path] = Field(default=None)
    max_file_size_mb: int = Field(default=100, ge=1, le=1000)
    backup_count: int = Field(default=5, ge=1, le=50)
    
    # Console logging
    enable_console_logging: bool = Field(default=True)
    console_format: LogFormat = Field(default=LogFormat.COLORED)
    
    # Structured logging fields
    include_timestamp: bool = Field(default=True)
    include_level: bool = Field(default=True)
    include_logger_name: bool = Field(default=True)
    include_thread_info: bool = Field(default=False)
    include_process_info: bool = Field(default=False)
    
    # External logging
    sentry_dsn: Optional[str] = Field(default=None)
    enable_sentry: bool = Field(default=False)
    
    class Config:
        env_prefix = "LOG_"


class TranslationSettings(BaseSettings):
    """Translation-specific settings"""
    
    # Default translation parameters
    default_source_language: str = Field(default="auto")
    default_target_language: str = Field(default="vi")
    default_style: str = Field(default="conversational")
    
    # Performance settings
    default_timeout_seconds: int = Field(default=30, ge=5, le=300)
    max_concurrent_requests: int = Field(default=10, ge=1, le=100)
    max_batch_size: int = Field(default=100, ge=1, le=1000)
    
    # Retry settings
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: float = Field(default=1.0, ge=0.1, le=60.0)
    retry_exponential_base: float = Field(default=2.0, ge=1.0, le=10.0)
    
    # Rate limiting
    enable_rate_limiting: bool = Field(default=True)
    default_requests_per_minute: int = Field(default=60, ge=1, le=1000)
    
    # Quality and validation
    enable_input_validation: bool = Field(default=True)
    max_text_length: int = Field(default=50000, ge=100, le=1000000)
    min_text_length: int = Field(default=1, ge=1, le=100)
    
    # Fallback behavior
    enable_provider_fallback: bool = Field(default=True)
    fallback_timeout_seconds: int = Field(default=10, ge=1, le=60)
    
    class Config:
        env_prefix = "TRANSLATION_"


class DatabaseSettings(BaseSettings):
    """Database configuration (if needed for caching/metrics)"""
    
    enable_database: bool = Field(default=False)
    database_url: Optional[str] = Field(default=None)
    
    # Connection pool settings
    max_connections: int = Field(default=10, ge=1, le=100)
    min_connections: int = Field(default=1, ge=1, le=10)
    connection_timeout_seconds: int = Field(default=30, ge=5, le=300)
    
    # Caching
    enable_result_caching: bool = Field(default=False)
    cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    max_cache_size: int = Field(default=10000, ge=100, le=1000000)
    
    class Config:
        env_prefix = "DB_"


class ObservabilitySettings(BaseSettings):
    """Observability configuration"""
    
    # Metrics
    enable_metrics: bool = Field(default=True)
    metrics_port: int = Field(default=9090, ge=1024, le=65535)
    metrics_path: str = Field(default="/metrics")
    
    # Tracing
    enable_tracing: bool = Field(default=False)
    tracing_endpoint: Optional[str] = Field(default=None)
    tracing_service_name: str = Field(default="ai-translation-framework")
    tracing_sample_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    
    # Health checks
    enable_health_checks: bool = Field(default=True)
    health_check_interval_seconds: int = Field(default=30, ge=10, le=300)
    health_check_timeout_seconds: int = Field(default=5, ge=1, le=30)
    
    class Config:
        env_prefix = "OBSERVABILITY_"


class Settings(BaseSettings):
    """
    Main application settings.
    
    Loads configuration from environment variables, config files, and defaults.
    """
    
    # Application info
    app_name: str = Field(default="AI Translation Framework")
    app_version: str = Field(default="2.0.0")
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    
    # Configuration files
    config_dir: Path = Field(default=Path("config"))
    providers_config_file: str = Field(default="providers.yaml")
    
    # Component settings
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    translation: TranslationSettings = Field(default_factory=TranslationSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    
    # Providers configuration (loaded separately)
    providers: Optional[ProvidersConfig] = Field(default=None)
    
    @validator('config_dir')
    def validate_config_dir(cls, v):
        """Ensure config directory exists"""
        if isinstance(v, str):
            v = Path(v)
        if not v.exists():
            v.mkdir(parents=True, exist_ok=True)
        return v
    
    @validator('debug')
    def sync_debug_with_environment(cls, v, values):
        """Sync debug flag with environment"""
        env = values.get('environment')
        if env == Environment.DEVELOPMENT and v is None:
            return True
        elif env == Environment.PRODUCTION and v is True:
            # Force debug off in production unless explicitly set
            return False
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.environment == Environment.TESTING
    
    @property
    def providers_config_path(self) -> Path:
        """Get full path to providers config file"""
        return self.config_dir / self.providers_config_file
    
    def get_log_level(self) -> str:
        """Get effective log level based on environment and debug flag"""
        if self.debug:
            return LogLevel.DEBUG
        return self.logging.level
    
    class Config:
        env_prefix = "APP_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Allow extra fields for extensibility
        extra = "allow"
        
        # JSON schema generation
        schema_extra = {
            "example": {
                "app_name": "AI Translation Framework",
                "environment": "development",
                "debug": True,
                "config_dir": "config",
                "logging": {
                    "level": "INFO",
                    "format": "json",
                    "enable_file_logging": True
                },
                "translation": {
                    "default_target_language": "vi",
                    "max_concurrent_requests": 10,
                    "enable_rate_limiting": True
                }
            }
        }