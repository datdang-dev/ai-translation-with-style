"""Translation request models"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid


class TranslationMode(str, Enum):
    """Translation processing modes"""
    SINGLE = "single"
    BATCH = "batch"
    STREAMING = "streaming"


class SourceLanguage(str, Enum):
    """Supported source languages"""
    AUTO = "auto"
    ENGLISH = "en"
    JAPANESE = "ja"
    KOREAN = "ko"
    CHINESE_SIMPLIFIED = "zh-CN"
    CHINESE_TRADITIONAL = "zh-TW"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    ARABIC = "ar"


class TargetLanguage(str, Enum):
    """Supported target languages"""
    VIETNAMESE = "vi"
    ENGLISH = "en"
    JAPANESE = "ja"
    KOREAN = "ko"
    CHINESE_SIMPLIFIED = "zh-CN"
    CHINESE_TRADITIONAL = "zh-TW"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    ARABIC = "ar"


class TranslationStyle(str, Enum):
    """Translation style preferences"""
    FORMAL = "formal"
    CASUAL = "casual"
    LITERARY = "literary"
    TECHNICAL = "technical"
    CONVERSATIONAL = "conversational"
    GAME_DIALOGUE = "game_dialogue"
    SUBTITLE = "subtitle"


class TranslationRequest(BaseModel):
    """
    A translation request containing text to be translated and processing parameters.
    
    This is the core model that flows through the entire translation pipeline.
    """
    
    # Core fields
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str = Field(..., min_length=1, max_length=50000, description="Text to translate")
    source_language: SourceLanguage = Field(default=SourceLanguage.AUTO)
    target_language: TargetLanguage = Field(default=TargetLanguage.VIETNAMESE)
    
    # Provider selection
    provider_name: Optional[str] = Field(default=None, description="Specific provider to use")
    model_name: Optional[str] = Field(default=None, description="Specific model to use")
    
    # Translation parameters
    style: TranslationStyle = Field(default=TranslationStyle.CONVERSATIONAL)
    context: Optional[str] = Field(default=None, max_length=5000, description="Additional context")
    custom_instructions: Optional[str] = Field(default=None, max_length=1000)
    
    # Processing options
    mode: TranslationMode = Field(default=TranslationMode.SINGLE)
    priority: int = Field(default=5, ge=1, le=10, description="Request priority (1=highest, 10=lowest)")
    timeout_seconds: Optional[int] = Field(default=30, ge=5, le=300)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    
    @validator('text')
    def validate_text(cls, v):
        """Validate that text is not just whitespace"""
        if not v.strip():
            raise ValueError("Text cannot be empty or only whitespace")
        return v.strip()
    
    @validator('tags')
    def validate_tags(cls, v):
        """Ensure tags are unique and valid"""
        if len(v) != len(set(v)):
            raise ValueError("Tags must be unique")
        return v
    
    def __str__(self) -> str:
        return f"TranslationRequest(id={self.request_id[:8]}, {self.source_language}->{self.target_language})"
    
    def __repr__(self) -> str:
        return (
            f"TranslationRequest(request_id='{self.request_id}', "
            f"text='{self.text[:50]}...', "
            f"source_language='{self.source_language}', "
            f"target_language='{self.target_language}')"
        )


class BatchTranslationRequest(BaseModel):
    """
    A batch of translation requests to be processed together.
    """
    
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    requests: List[TranslationRequest] = Field(..., min_items=1, max_items=1000)
    
    # Batch-level settings
    max_concurrent: int = Field(default=5, ge=1, le=50)
    batch_timeout_seconds: Optional[int] = Field(default=300, ge=30, le=3600)
    fail_fast: bool = Field(default=False, description="Stop on first failure")
    
    # Shared settings for all requests in batch
    shared_provider: Optional[str] = Field(default=None)
    shared_model: Optional[str] = Field(default=None)
    shared_style: Optional[TranslationStyle] = Field(default=None)
    
    @validator('requests')
    def validate_requests(cls, v):
        """Ensure all requests have unique IDs"""
        request_ids = [req.request_id for req in v]
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("All requests must have unique IDs")
        return v
    
    def apply_shared_settings(self) -> None:
        """Apply shared settings to all requests that don't have them specified"""
        for request in self.requests:
            if self.shared_provider and not request.provider_name:
                request.provider_name = self.shared_provider
            if self.shared_model and not request.model_name:
                request.model_name = self.shared_model
            if self.shared_style and request.style == TranslationStyle.CONVERSATIONAL:
                request.style = self.shared_style
    
    def __len__(self) -> int:
        return len(self.requests)
    
    def __str__(self) -> str:
        return f"BatchTranslationRequest(id={self.batch_id[:8]}, {len(self.requests)} requests)"