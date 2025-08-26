"""
Text Standardizer for plain text content
"""

from typing import Any, List
from services.standardizer.base_standardizer import BaseStandardizer
from services.models import Chunk, StandardizedContent, FormatType


class TextStandardizer(BaseStandardizer):
    """Standardizer for plain text content"""
    
    def get_format_type(self) -> FormatType:
        """Get the format type this standardizer handles"""
        return FormatType.TEXT
    
    def standardize(self, content: Any) -> StandardizedContent:
        """Standardize plain text content into chunks"""
        if not isinstance(content, str):
            raise ValueError("Text standardizer expects string content")
        
        # For plain text, create a single chunk
        chunk = self.create_chunk(
            text=content,
            is_text=True,
            chunk_type="text",
            metadata={"format": "plain_text"}
        )
        
        return self.create_standardized_content(
            chunks=[chunk],
            original_content=content,
            metadata={"standardizer": "TextStandardizer"}
        )
    
    def reconstruct(self, standardized_content: StandardizedContent) -> Any:
        """Reconstruct text from standardized chunks"""
        if not standardized_content.chunks:
            return ""
        
        # For text, just concatenate all chunks
        return " ".join(chunk.standard for chunk in standardized_content.chunks if chunk.standard)
    
    def validate(self, content: Any) -> bool:
        """Validate if content is plain text"""
        return isinstance(content, str) and len(content.strip()) > 0
