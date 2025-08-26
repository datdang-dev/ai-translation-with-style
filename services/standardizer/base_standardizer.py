"""
Base standardizer interface and common utilities
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
from services.models import Chunk, StandardizedContent, FormatType, StandardizationError


class IStandardizer(ABC):
    """Interface for format-specific standardizers"""
    
    @abstractmethod
    def get_format_type(self) -> FormatType:
        """Get the format type this standardizer handles"""
        pass
    
    @abstractmethod
    def standardize(self, content: Any) -> StandardizedContent:
        """Standardize content into chunks"""
        pass
    
    @abstractmethod
    def reconstruct(self, standardized_content: StandardizedContent) -> Any:
        """Reconstruct content from standardized chunks"""
        pass
    
    @abstractmethod
    def validate(self, content: Any) -> bool:
        """Validate if content matches expected format"""
        pass
    
    def get_schema_version(self) -> str:
        """Get schema version for this standardizer"""
        return "1.0"


class BaseStandardizer(IStandardizer):
    """Base implementation with common functionality"""
    
    def __init__(self):
        self.schema_version = "1.0"
    
    def create_chunk(self, 
                    text: str, 
                    is_text: bool = True, 
                    chunk_type: str = "text",
                    metadata: dict = None) -> Chunk:
        """Helper to create standardized chunks"""
        return Chunk(
            is_text=is_text,
            original=text,
            standard=text if is_text else "",
            chunk_type=chunk_type,
            metadata=metadata or {}
        )
    
    def create_standardized_content(self, 
                                  chunks: List[Chunk], 
                                  original_content: Any,
                                  metadata: dict = None) -> StandardizedContent:
        """Helper to create standardized content"""
        return StandardizedContent(
            chunks=chunks,
            format_type=self.get_format_type(),
            original_content=original_content,
            schema_version=self.schema_version,
            processing_metadata=metadata or {}
        )
    
    def validate_chunks(self, chunks: List[Chunk]) -> bool:
        """Basic chunk validation"""
        if not chunks:
            return False
        
        # Check that all chunks have required fields
        for chunk in chunks:
            if not hasattr(chunk, 'is_text') or not hasattr(chunk, 'original'):
                return False
        
        return True
