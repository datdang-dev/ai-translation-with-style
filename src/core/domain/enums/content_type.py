"""
Content Type Enumeration

Defines the types of content that can be processed by the translation system.
"""

from enum import Enum


class ContentType(Enum):
    """
    Types of content that can be translated.
    
    Each content type may require different processing strategies,
    chunking approaches, and validation rules.
    """
    
    # Text-based content
    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    HTML = "html"
    
    # Structured data
    JSON = "json"
    XML = "xml"
    YAML = "yaml"
    
    # Game content
    GAME_SCRIPT = "game_script"
    RENPY_SCRIPT = "renpy_script"
    DIALOGUE_TREE = "dialogue_tree"
    
    # Subtitles and captions
    SRT = "srt"
    VTT = "vtt"
    ASS = "ass"
    
    # Document formats
    CSV = "csv"
    TSV = "tsv"
    
    # Custom formats
    CUSTOM = "custom"
    
    def __str__(self) -> str:
        return self.value
    
    @property
    def is_structured(self) -> bool:
        """Check if content type is structured data."""
        return self in {
            ContentType.JSON,
            ContentType.XML, 
            ContentType.YAML
        }
    
    @property
    def is_game_content(self) -> bool:
        """Check if content type is game-related."""
        return self in {
            ContentType.GAME_SCRIPT,
            ContentType.RENPY_SCRIPT,
            ContentType.DIALOGUE_TREE
        }
    
    @property
    def is_subtitle_format(self) -> bool:
        """Check if content type is subtitle/caption format."""
        return self in {
            ContentType.SRT,
            ContentType.VTT,
            ContentType.ASS
        }
    
    @property
    def requires_context_preservation(self) -> bool:
        """Check if content type requires context preservation."""
        return self in {
            ContentType.GAME_SCRIPT,
            ContentType.RENPY_SCRIPT,
            ContentType.DIALOGUE_TREE,
            ContentType.MARKDOWN,
            ContentType.HTML
        }
    
    @classmethod
    def from_file_extension(cls, extension: str) -> 'ContentType':
        """
        Determine content type from file extension.
        
        Args:
            extension: File extension (with or without dot)
            
        Returns:
            ContentType enum value
            
        Raises:
            ValueError: If extension is not recognized
        """
        # Normalize extension
        ext = extension.lower().lstrip('.')
        
        extension_mapping = {
            'txt': cls.PLAIN_TEXT,
            'text': cls.PLAIN_TEXT,
            'md': cls.MARKDOWN,
            'markdown': cls.MARKDOWN,
            'html': cls.HTML,
            'htm': cls.HTML,
            'json': cls.JSON,
            'xml': cls.XML,
            'yaml': cls.YAML,
            'yml': cls.YAML,
            'rpy': cls.RENPY_SCRIPT,
            'srt': cls.SRT,
            'vtt': cls.VTT,
            'ass': cls.ASS,
            'csv': cls.CSV,
            'tsv': cls.TSV
        }
        
        if ext in extension_mapping:
            return extension_mapping[ext]
        else:
            return cls.CUSTOM
    
    @property
    def default_chunk_strategy(self) -> str:
        """Get the default chunk strategy for this content type."""
        if self.is_structured:
            return "structural"
        elif self.is_game_content:
            return "semantic"
        elif self.is_subtitle_format:
            return "temporal"
        else:
            return "semantic"