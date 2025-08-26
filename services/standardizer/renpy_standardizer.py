"""
Renpy format standardizer
Handles Renpy script format with dialogue and code separation
"""

import re
from typing import Any, List, Optional
from services.models import Chunk, StandardizedContent, FormatType, StandardizationError
from .base_standardizer import BaseStandardizer


class RenpyStandardizer(BaseStandardizer):
    """Standardizer for Renpy script format"""
    
    def __init__(self):
        super().__init__()
        self.dialogue_patterns = [
            # Standard dialogue patterns
            r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s+"([^"]+)"(\s*)$',  # character "dialogue"
            r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s+\"([^\"]+)\"(\s*)$',  # character "dialogue" with quotes
            r'^(\s*)"([^"]+)"(\s*)$',  # "narrator dialogue"
            r'^(\s*)\"([^\"]+)\"(\s*)$',  # "narrator dialogue" with quotes
            
            # Dialogue with expressions/modifiers
            r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s+([a-zA-Z0-9_]+)\s+"([^"]+)"(\s*)$',  # character emotion "dialogue"
            
            # Text within special blocks
            r'^(\s*)# "([^"]+)"(\s*)$',  # Commented dialogue for translation
        ]
        
        self.code_patterns = [
            # Labels and jumps
            r'^(\s*)label\s+',
            r'^(\s*)jump\s+',
            r'^(\s*)call\s+',
            
            # Conditionals and flow control
            r'^(\s*)if\s+',
            r'^(\s*)elif\s+',
            r'^(\s*)else\s*:',
            r'^(\s*)while\s+',
            r'^(\s*)for\s+',
            
            # Variable assignments
            r'^(\s*)\$\s+',
            r'^(\s*)define\s+',
            r'^(\s*)default\s+',
            
            # Scene and show commands
            r'^(\s*)scene\s+',
            r'^(\s*)show\s+',
            r'^(\s*)hide\s+',
            r'^(\s*)with\s+',
            
            # Menu and choice blocks (structure only)
            r'^(\s*)menu\s*:',
            r'^(\s*)return\s*$',
            r'^(\s*)pause\s*',
            
            # Comments and empty lines
            r'^(\s*)#.*$',
            r'^(\s*)$',
        ]
    
    def get_format_type(self) -> FormatType:
        return FormatType.RENPY
    
    def validate(self, content: Any) -> bool:
        """Validate if content looks like Renpy script"""
        if not isinstance(content, str):
            return False
        
        lines = content.strip().split('\n')
        if not lines:
            return False
        
        # Check for common Renpy patterns
        renpy_indicators = 0
        total_significant_lines = 0
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            total_significant_lines += 1
            
            # Check for Renpy-specific syntax
            if (any(re.match(pattern, line) for pattern in self.code_patterns) or
                any(re.match(pattern, line) for pattern in self.dialogue_patterns)):
                renpy_indicators += 1
        
        # If more than 30% of lines look like Renpy, consider it valid
        if total_significant_lines == 0:
            return False
        
        return (renpy_indicators / total_significant_lines) > 0.3
    
    def standardize(self, content: Any) -> StandardizedContent:
        """Standardize Renpy script content"""
        if not isinstance(content, str):
            raise StandardizationError("Renpy content must be a string")
        
        if not self.validate(content):
            raise StandardizationError("Content does not appear to be valid Renpy script")
        
        lines = content.split('\n')
        chunks = []
        
        for i, line in enumerate(lines):
            chunk = self._process_line(line, i)
            chunks.append(chunk)
        
        metadata = {
            'total_lines': len(lines),
            'dialogue_lines': sum(1 for chunk in chunks if chunk.is_text),
            'code_lines': sum(1 for chunk in chunks if not chunk.is_text)
        }
        
        return self.create_standardized_content(chunks, content, metadata)
    
    def _process_line(self, line: str, line_number: int) -> Chunk:
        """Process a single line of Renpy script"""
        original_line = line
        
        # Try to match dialogue patterns
        for pattern in self.dialogue_patterns:
            match = re.match(pattern, line)
            if match:
                return self._create_dialogue_chunk(line, match, line_number)
        
        # If not dialogue, it's code/structure
        return self._create_code_chunk(line, line_number)
    
    def _create_dialogue_chunk(self, line: str, match: re.Match, line_number: int) -> Chunk:
        """Create a chunk for dialogue line"""
        groups = match.groups()
        
        # Extract dialogue text based on pattern
        if len(groups) >= 3:
            # Most patterns have dialogue as one of the middle groups
            dialogue_text = None
            for group in groups:
                if group and len(group.strip()) > 0 and not group.isspace():
                    # Look for the actual dialogue content (longest meaningful group)
                    if dialogue_text is None or len(group) > len(dialogue_text):
                        dialogue_text = group
            
            if dialogue_text:
                dialogue_text = dialogue_text.strip()
            else:
                dialogue_text = line.strip()
        else:
            dialogue_text = line.strip()
        
        metadata = {
            'line_number': line_number,
            'line_type': 'dialogue',
            'raw_line': line
        }
        
        return Chunk(
            is_text=True,
            original=line,
            standard=dialogue_text,
            chunk_type="dialogue",
            metadata=metadata
        )
    
    def _create_code_chunk(self, line: str, line_number: int) -> Chunk:
        """Create a chunk for code/structure line"""
        metadata = {
            'line_number': line_number,
            'line_type': 'code',
            'raw_line': line
        }
        
        return Chunk(
            is_text=False,
            original=line,
            standard="",  # Code chunks don't need standardization
            chunk_type="code",
            metadata=metadata
        )
    
    def reconstruct(self, standardized_content: StandardizedContent) -> str:
        """Reconstruct Renpy script from standardized content"""
        if standardized_content.format_type != FormatType.RENPY:
            raise StandardizationError("Content is not Renpy format")
        
        reconstructed_lines = []
        
        for chunk in standardized_content.chunks:
            if chunk.is_text and chunk.translation:
                # Reconstruct dialogue line with translation
                reconstructed_line = self._reconstruct_dialogue_line(chunk)
            else:
                # Keep code lines as-is
                reconstructed_line = chunk.original
            
            reconstructed_lines.append(reconstructed_line)
        
        return '\n'.join(reconstructed_lines)
    
    def _reconstruct_dialogue_line(self, chunk: Chunk) -> str:
        """Reconstruct a dialogue line with translation"""
        original_line = chunk.original
        translation = chunk.translation or chunk.standard
        
        # Try to replace the dialogue part with translation
        for pattern in self.dialogue_patterns:
            match = re.match(pattern, original_line)
            if match:
                return self._replace_dialogue_in_line(original_line, match, translation)
        
        # Fallback: return translation as comment
        return f"# {translation}"
    
    def _replace_dialogue_in_line(self, original_line: str, match: re.Match, translation: str) -> str:
        """Replace dialogue text in line while preserving structure"""
        groups = match.groups()
        
        # Simple replacement strategy: find quoted text and replace it
        # This is a basic implementation - could be more sophisticated
        if '"' in original_line:
            # Find the quoted text and replace it
            parts = original_line.split('"')
            if len(parts) >= 3:
                # Replace the content between first pair of quotes
                parts[1] = translation
                return '"'.join(parts)
        
        # Fallback: try to preserve line structure
        return original_line.replace(match.groups()[-2] if len(match.groups()) > 1 else match.group(0), 
                                   translation, 1)
    
    def extract_translatable_text(self, content: str) -> List[str]:
        """Extract only translatable text for quick processing"""
        standardized = self.standardize(content)
        return standardized.get_translatable_texts()
    
    def apply_translations(self, content: str, translations: List[str]) -> str:
        """Apply translations to content efficiently"""
        standardized = self.standardize(content)
        translatable_chunks = standardized.get_translatable_chunks()
        
        if len(translations) != len(translatable_chunks):
            raise StandardizationError(
                f"Translation count mismatch: {len(translations)} translations "
                f"for {len(translatable_chunks)} chunks"
            )
        
        # Apply translations to chunks
        for chunk, translation in zip(translatable_chunks, translations):
            chunk.translation = translation
        
        return self.reconstruct(standardized)