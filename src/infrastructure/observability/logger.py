"""Structured logging with observability support"""

import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import structlog
from structlog.typing import FilteringBoundLogger

from ..config import LoggingSettings, LogLevel, LogFormat


# Global logger cache
_loggers: Dict[str, FilteringBoundLogger] = {}
_configured = False


class StructuredLogger:
    """
    Wrapper around structlog for consistent logging across the application.
    
    Provides structured logging with context preservation and observability integration.
    """
    
    def __init__(self, name: str):
        self.name = name
        self._logger = structlog.get_logger(name)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context"""
        self._logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with context"""
        self._logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context"""
        self._logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with context"""
        self._logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with context"""
        self._logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback"""
        self._logger.exception(message, **kwargs)
    
    def bind(self, **kwargs) -> 'StructuredLogger':
        """Create a new logger with bound context"""
        bound_logger = StructuredLogger(self.name)
        bound_logger._logger = self._logger.bind(**kwargs)
        return bound_logger
    
    def with_context(self, **kwargs) -> 'StructuredLogger':
        """Alias for bind() for better readability"""
        return self.bind(**kwargs)


def setup_logging(settings: LoggingSettings) -> None:
    """
    Configure structured logging based on settings.
    
    Args:
        settings: Logging configuration
    """
    global _configured
    
    if _configured:
        return
    
    # Configure processors based on format
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add context processors
    if settings.include_process_info:
        processors.append(structlog.processors.add_log_level)
    
    if settings.include_thread_info:
        processors.append(structlog.dev.set_exc_info)
    
    # Configure output format
    if settings.format == LogFormat.JSON:
        processors.append(structlog.processors.JSONRenderer())
    elif settings.format == LogFormat.COLORED:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:  # TEXT
        processors.append(structlog.dev.ConsoleRenderer(colors=False))
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    _setup_stdlib_logging(settings)
    
    # Setup Sentry integration if enabled
    if settings.enable_sentry and settings.sentry_dsn:
        _setup_sentry_logging(settings)
    
    _configured = True


def _setup_stdlib_logging(settings: LoggingSettings) -> None:
    """Configure standard library logging"""
    
    # Get log level
    log_level = getattr(logging, settings.level.value)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if settings.enable_console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        if settings.console_format == LogFormat.JSON:
            formatter = logging.Formatter(
                '{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
            )
        elif settings.console_format == LogFormat.COLORED:
            # Use a simple format for colored output (structlog will handle colors)
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
            )
        else:  # TEXT
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
            )
        
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if settings.enable_file_logging and settings.log_file:
        log_file = Path(settings.log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=settings.max_file_size_mb * 1024 * 1024,
            backupCount=settings.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        
        # Always use JSON format for file logging
        file_formatter = logging.Formatter(
            '{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s","module":"%(module)s","function":"%(funcName)s","line":%(lineno)d}'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def _setup_sentry_logging(settings: LoggingSettings) -> None:
    """Setup Sentry error tracking"""
    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        sentry_logging = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[sentry_logging],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
        )
        
    except ImportError:
        # Sentry SDK not installed, log warning
        logger = structlog.get_logger("sentry")
        logger.warning("Sentry SDK not installed, error tracking disabled")


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically module name)
        
    Returns:
        StructuredLogger instance
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    
    return _loggers[name]


def create_request_logger(request_id: str, user_id: Optional[str] = None) -> StructuredLogger:
    """
    Create a logger with request context bound.
    
    Args:
        request_id: Unique request identifier
        user_id: Optional user identifier
        
    Returns:
        Logger with request context
    """
    logger = get_logger("request")
    
    context = {"request_id": request_id}
    if user_id:
        context["user_id"] = user_id
    
    return logger.bind(**context)


def create_translation_logger(
    request_id: str, 
    provider: str,
    model: Optional[str] = None
) -> StructuredLogger:
    """
    Create a logger with translation context bound.
    
    Args:
        request_id: Translation request ID
        provider: Provider name
        model: Optional model name
        
    Returns:
        Logger with translation context
    """
    logger = get_logger("translation")
    
    context = {
        "request_id": request_id,
        "provider": provider,
    }
    
    if model:
        context["model"] = model
    
    return logger.bind(**context)


def log_performance_metrics(
    logger: StructuredLogger,
    operation: str,
    duration_ms: int,
    **metrics
) -> None:
    """
    Log performance metrics in a structured way.
    
    Args:
        logger: Logger instance
        operation: Operation name
        duration_ms: Duration in milliseconds
        **metrics: Additional metrics to log
    """
    logger.info(
        "Performance metrics",
        operation=operation,
        duration_ms=duration_ms,
        **metrics
    )


def log_error_with_context(
    logger: StructuredLogger,
    error: Exception,
    operation: str,
    **context
) -> None:
    """
    Log error with full context and traceback.
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        operation: Operation that failed
        **context: Additional context
    """
    logger.error(
        f"Operation failed: {operation}",
        error_type=type(error).__name__,
        error_message=str(error),
        operation=operation,
        **context,
        exc_info=True
    )