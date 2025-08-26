"""
Standardizer service for managing multiple format standardizers
"""

from typing import Any, Dict, List, Optional
from services.models import StandardizedContent, FormatType, StandardizationError
from .base_standardizer import IStandardizer
from .renpy_standardizer import RenpyStandardizer
from .json_standardizer import JsonStandardizer
from .text_standardizer import TextStandardizer


class StandardizerService:
    """Service for managing and routing to format-specific standardizers"""
    
    def __init__(self):
        self.standardizers: Dict[FormatType, IStandardizer] = {}
        self._register_default_standardizers()
    
    def _register_default_standardizers(self):
        """Register built-in standardizers"""
        self.register_standardizer(RenpyStandardizer())
        self.register_standardizer(JsonStandardizer())
        self.register_standardizer(TextStandardizer())
    
    def register_standardizer(self, standardizer: IStandardizer):
        """Register a new standardizer"""
        format_type = standardizer.get_format_type()
        self.standardizers[format_type] = standardizer
    
    def get_standardizer(self, format_type: FormatType) -> Optional[IStandardizer]:
        """Get standardizer for specific format"""
        return self.standardizers.get(format_type)
    
    def get_supported_formats(self) -> List[FormatType]:
        """Get list of supported formats"""
        return list(self.standardizers.keys())
    
    def detect_format(self, content: Any) -> Optional[FormatType]:
        """Auto-detect content format"""
        # Try each standardizer's validation
        for format_type, standardizer in self.standardizers.items():
            try:
                if standardizer.validate(content):
                    return format_type
            except Exception:
                continue  # Validation failed, try next
        
        return None
    
    def standardize(self, content: Any, format_type: FormatType = None) -> StandardizedContent:
        """Standardize content using appropriate standardizer"""
        # Auto-detect format if not specified
        if format_type is None:
            format_type = self.detect_format(content)
            if format_type is None:
                raise StandardizationError("Could not detect content format")
        
        # Get appropriate standardizer
        standardizer = self.get_standardizer(format_type)
        if standardizer is None:
            raise StandardizationError(f"No standardizer available for format: {format_type}")
        
        try:
            return standardizer.standardize(content)
        except Exception as e:
            raise StandardizationError(f"Standardization failed for {format_type}: {e}")
    
    def reconstruct(self, standardized_content: StandardizedContent) -> Any:
        """Reconstruct content from standardized format"""
        format_type = standardized_content.format_type
        standardizer = self.get_standardizer(format_type)
        
        if standardizer is None:
            raise StandardizationError(f"No standardizer available for format: {format_type}")
        
        try:
            return standardizer.reconstruct(standardized_content)
        except Exception as e:
            raise StandardizationError(f"Reconstruction failed for {format_type}: {e}")
    
    def standardize_renpy(self, text: str) -> StandardizedContent:
        """Convenience method for Renpy standardization"""
        return self.standardize(text, FormatType.RENPY)
    
    def standardize_json(self, data: Any) -> StandardizedContent:
        """Convenience method for JSON standardization"""
        return self.standardize(data, FormatType.JSON)
    
    def reconstruct_renpy(self, standardized_content: StandardizedContent) -> str:
        """Convenience method for Renpy reconstruction"""
        if standardized_content.format_type != FormatType.RENPY:
            raise StandardizationError("Content is not Renpy format")
        return self.reconstruct(standardized_content)
    
    def reconstruct_json(self, standardized_content: StandardizedContent) -> Any:
        """Convenience method for JSON reconstruction"""
        if standardized_content.format_type != FormatType.JSON:
            raise StandardizationError("Content is not JSON format")
        return self.reconstruct(standardized_content)
    
    def validate_content(self, content: Any, format_type: FormatType) -> bool:
        """Validate content against specific format"""
        standardizer = self.get_standardizer(format_type)
        if standardizer is None:
            return False
        
        try:
            return standardizer.validate(content)
        except Exception:
            return False
    
    def get_translatable_text(self, content: Any, format_type: FormatType = None) -> List[str]:
        """Extract translatable text from content"""
        standardized = self.standardize(content, format_type)
        return standardized.get_translatable_texts()
    
    def apply_translations(self, 
                          content: Any, 
                          translations: List[str], 
                          format_type: FormatType = None) -> Any:
        """Apply translations to content and reconstruct"""
        standardized = self.standardize(content, format_type)
        translatable_chunks = standardized.get_translatable_chunks()
        
        if len(translations) != len(translatable_chunks):
            raise StandardizationError(
                f"Translation count mismatch: expected {len(translatable_chunks)}, "
                f"got {len(translations)}"
            )
        
        # Apply translations to chunks
        for chunk, translation in zip(translatable_chunks, translations):
            chunk.translation = translation
        
        return self.reconstruct(standardized)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            'supported_formats': [fmt.value for fmt in self.get_supported_formats()],
            'standardizer_count': len(self.standardizers),
            'format_details': {
                fmt.value: {
                    'standardizer_class': type(standardizer).__name__,
                    'schema_version': getattr(standardizer, 'schema_version', 'unknown')
                }
                for fmt, standardizer in self.standardizers.items()
            }
        }
