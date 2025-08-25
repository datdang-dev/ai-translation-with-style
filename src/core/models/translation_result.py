"""Translation result models"""

from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid


class TranslationStatus(str, Enum):
    """Translation processing status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ErrorType(str, Enum):
    """Types of translation errors"""
    PROVIDER_ERROR = "provider_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    TIMEOUT_ERROR = "timeout_error"
    VALIDATION_ERROR = "validation_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    UNKNOWN_ERROR = "unknown_error"


class TranslationError(BaseModel):
    """Detailed error information for failed translations"""
    
    error_type: ErrorType
    error_code: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)
    retry_after: Optional[int] = Field(default=None, description="Seconds to wait before retry")
    is_retryable: bool = Field(default=True)
    
    def __str__(self) -> str:
        return f"{self.error_type}: {self.message}"


class TranslationMetrics(BaseModel):
    """Performance and quality metrics for a translation"""
    
    # Timing metrics
    processing_time_ms: int = Field(ge=0)
    queue_time_ms: int = Field(default=0, ge=0)
    
    # Token metrics
    input_tokens: Optional[int] = Field(default=None, ge=0)
    output_tokens: Optional[int] = Field(default=None, ge=0)
    
    # Quality metrics
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    
    # Provider metrics
    provider_name: str
    model_name: Optional[str] = None
    api_version: Optional[str] = None
    
    # Resource usage
    retry_count: int = Field(default=0, ge=0)
    rate_limit_hit: bool = Field(default=False)


class TranslationResult(BaseModel):
    """
    Result of a translation request, containing the translated text and metadata.
    
    This is the primary output model of the translation pipeline.
    """
    
    # Core result data
    request_id: str = Field(..., description="ID of the original request")
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: TranslationStatus
    
    # Translation output
    translated_text: Optional[str] = Field(default=None)
    original_text: str = Field(..., description="Original text that was translated")
    
    # Language information
    detected_source_language: Optional[str] = Field(default=None)
    target_language: str
    
    # Error information (if status is FAILED)
    error: Optional[TranslationError] = None
    
    # Performance metrics
    metrics: Optional[TranslationMetrics] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        """Check if translation was successful"""
        return self.status == TranslationStatus.COMPLETED and self.translated_text is not None
    
    @property
    def is_failed(self) -> bool:
        """Check if translation failed"""
        return self.status == TranslationStatus.FAILED
    
    @property
    def is_pending(self) -> bool:
        """Check if translation is still pending"""
        return self.status in [TranslationStatus.PENDING, TranslationStatus.IN_PROGRESS]
    
    @property
    def total_processing_time_ms(self) -> Optional[int]:
        """Calculate total processing time if timestamps are available"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None
    
    def mark_started(self) -> None:
        """Mark translation as started"""
        self.status = TranslationStatus.IN_PROGRESS
        self.started_at = datetime.now(timezone.utc)
    
    def mark_completed(self, translated_text: str, metrics: Optional[TranslationMetrics] = None) -> None:
        """Mark translation as completed successfully"""
        self.status = TranslationStatus.COMPLETED
        self.translated_text = translated_text
        self.completed_at = datetime.now(timezone.utc)
        if metrics:
            self.metrics = metrics
    
    def mark_failed(self, error: TranslationError) -> None:
        """Mark translation as failed"""
        self.status = TranslationStatus.FAILED
        self.error = error
        self.completed_at = datetime.now(timezone.utc)
    
    def mark_timeout(self) -> None:
        """Mark translation as timed out"""
        self.status = TranslationStatus.TIMEOUT
        self.completed_at = datetime.now(timezone.utc)
        self.error = TranslationError(
            error_type=ErrorType.TIMEOUT_ERROR,
            message="Translation request timed out",
            is_retryable=True
        )
    
    def __str__(self) -> str:
        status_emoji = {
            TranslationStatus.PENDING: "⏳",
            TranslationStatus.IN_PROGRESS: "🔄", 
            TranslationStatus.COMPLETED: "✅",
            TranslationStatus.FAILED: "❌",
            TranslationStatus.TIMEOUT: "⏰",
            TranslationStatus.CANCELLED: "🚫"
        }
        emoji = status_emoji.get(self.status, "❓")
        return f"{emoji} TranslationResult(id={self.result_id[:8]}, status={self.status})"


class BatchTranslationResult(BaseModel):
    """
    Result of a batch translation request.
    """
    
    batch_id: str
    results: List[TranslationResult] = Field(default_factory=list)
    
    # Batch-level metrics
    total_requests: int = Field(ge=0)
    successful_requests: int = Field(default=0, ge=0)
    failed_requests: int = Field(default=0, ge=0)
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Error summary
    errors_by_type: Dict[ErrorType, int] = Field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def is_completed(self) -> bool:
        """Check if all translations in batch are completed"""
        return len(self.results) == self.total_requests
    
    @property
    def total_processing_time_ms(self) -> Optional[int]:
        """Calculate total batch processing time"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None
    
    def add_result(self, result: TranslationResult) -> None:
        """Add a translation result to the batch"""
        self.results.append(result)
        
        if result.is_success:
            self.successful_requests += 1
        elif result.is_failed:
            self.failed_requests += 1
            if result.error:
                error_type = result.error.error_type
                self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
    
    def get_successful_results(self) -> List[TranslationResult]:
        """Get only successful translation results"""
        return [r for r in self.results if r.is_success]
    
    def get_failed_results(self) -> List[TranslationResult]:
        """Get only failed translation results"""
        return [r for r in self.results if r.is_failed]
    
    def __str__(self) -> str:
        return (
            f"BatchTranslationResult(id={self.batch_id[:8]}, "
            f"{self.successful_requests}/{self.total_requests} successful, "
            f"{self.success_rate:.1f}% success rate)"
        )