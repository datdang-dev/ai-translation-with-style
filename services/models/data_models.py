"""
Data models for the new translation architecture
Defines core data structures used across all layers
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import uuid


class FormatType(Enum):
    """Supported content formats"""
    RENPY = "renpy"
    JSON = "json"
    TEXT = "text"


class ProviderType(Enum):
    """Supported translation providers"""
    OPENROUTER = "openrouter"
    GOOGLE_TRANSLATE = "google_translate"
    AUTO = "auto"  # Let system choose best provider


@dataclass
class TranslationRequest:
    """Request for translation with all necessary metadata"""
    content: Any
    source_lang: str
    target_lang: str
    format_type: FormatType
    
    # Optional fields
    style: Optional[str] = None
    provider: ProviderType = ProviderType.AUTO
    metadata: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Ensure format_type and provider are enums"""
        if isinstance(self.format_type, str):
            self.format_type = FormatType(self.format_type.lower())
        if isinstance(self.provider, str):
            self.provider = ProviderType(self.provider.lower())


@dataclass
class TranslationResult:
    """Result of translation operation"""
    original: Any
    translated: Any
    provider: str
    
    # Performance metrics
    from_cache: bool = False
    processing_time: float = 0.0
    
    # Metadata
    source_lang: str = ""
    target_lang: str = ""
    format_type: FormatType = FormatType.TEXT
    metadata: Dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    completed_at: datetime = field(default_factory=datetime.now)
    
    # Quality metrics
    confidence_score: Optional[float] = None
    validation_passed: bool = True
    validation_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """Standardized chunk for content processing"""
    is_text: bool
    original: str
    
    # Standardized representation
    standard: str = ""
    
    # Translation result
    translation: str = ""
    
    # Metadata
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chunk_type: str = "text"  # text, tag, code, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set standard to original if not provided"""
        if not self.standard:
            self.standard = self.original if self.is_text else ""


@dataclass
class StandardizedContent:
    """Result of content standardization"""
    chunks: List[Chunk]
    format_type: FormatType
    original_content: Any
    
    # Metadata
    schema_version: str = "1.0"
    processing_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_translatable_chunks(self) -> List[Chunk]:
        """Get only chunks that need translation"""
        return [chunk for chunk in self.chunks if chunk.is_text and chunk.standard.strip()]
    
    def get_translatable_texts(self) -> List[str]:
        """Get list of texts that need translation"""
        return [chunk.standard for chunk in self.get_translatable_chunks()]


@dataclass
class BatchResult:
    """Result of batch translation operation"""
    total_requests: int
    successful_translations: int
    failed_translations: int
    
    # Results
    results: List[TranslationResult] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance metrics
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0
    cache_hit_rate: float = 0.0
    
    # Metadata
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_translations / self.total_requests) * 100
    
    def mark_completed(self):
        """Mark batch as completed and calculate final metrics"""
        self.completed_at = datetime.now()
        if self.successful_translations > 0:
            self.average_processing_time = self.total_processing_time / self.successful_translations


# Health and monitoring models
@dataclass
class HealthStatus:
    """Health status of a service or provider"""
    is_healthy: bool
    status_code: int
    message: str
    last_check: datetime
    response_time: float
    
    # Additional details
    details: Dict[str, Any] = field(default_factory=dict)
    check_count: int = 0
    consecutive_failures: int = 0
    
    @classmethod
    def healthy(cls, message: str = "OK", response_time: float = 0.0) -> 'HealthStatus':
        """Create healthy status"""
        return cls(
            is_healthy=True,
            status_code=200,
            message=message,
            last_check=datetime.now(),
            response_time=response_time
        )
    
    @classmethod
    def unhealthy(cls, message: str = "Service unavailable", status_code: int = 500) -> 'HealthStatus':
        """Create unhealthy status"""
        return cls(
            is_healthy=False,
            status_code=status_code,
            message=message,
            last_check=datetime.now(),
            response_time=0.0
        )


@dataclass
class ProviderStats:
    """Statistics for a translation provider"""
    name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_used: Optional[datetime] = None
    
    # Rate limiting info
    requests_per_minute: int = 0
    rate_limit_window_start: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    def record_request(self, success: bool, response_time: float):
        """Record a request outcome"""
        self.total_requests += 1
        self.last_used = datetime.now()
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # Update average response time
        if self.total_requests == 1:
            self.average_response_time = response_time
        else:
            self.average_response_time = (
                (self.average_response_time * (self.total_requests - 1) + response_time) 
                / self.total_requests
            )


# Configuration models
@dataclass
class ProviderConfig:
    """Configuration for a translation provider"""
    name: str
    enabled: bool = True
    priority: int = 1  # Lower number = higher priority
    max_requests_per_minute: int = 20
    timeout: float = 30.0
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResiliencyConfig:
    """Configuration for resiliency policies"""
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff_multiplier: float = 2.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    request_timeout: float = 30.0


@dataclass
class CacheConfig:
    """Configuration for caching"""
    enabled: bool = True
    ttl_seconds: int = 3600  # 1 hour default
    max_size: int = 1000
    backend: str = "memory"  # memory, redis
    redis_url: Optional[str] = None


# Error handling models
class TranslationError(Exception):
    """Base exception for translation errors"""
    def __init__(self, message: str, error_code: str = "UNKNOWN", details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()


class ProviderError(TranslationError):
    """Error from translation provider"""
    pass


class StandardizationError(TranslationError):
    """Error during content standardization"""
    pass


class ValidationError(TranslationError):
    """Error during translation validation"""
    pass


# Export all models
__all__ = [
    # Enums
    'FormatType', 'ProviderType',
    # Core models
    'TranslationRequest', 'TranslationResult', 'Chunk', 'StandardizedContent', 'BatchResult',
    # Monitoring models
    'HealthStatus', 'ProviderStats',
    # Configuration models
    'ProviderConfig', 'ResiliencyConfig', 'CacheConfig',
    # Exceptions
    'TranslationError', 'ProviderError', 'StandardizationError', 'ValidationError'
]
