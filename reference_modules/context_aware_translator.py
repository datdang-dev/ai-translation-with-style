"""
@brief ContextAwareTranslator: Context-aware translation với semantic grouping
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import re

class ContextStrategy(Enum):
    SEMANTIC_GROUPING = "semantic_grouping"
    WINDOW_BASED = "window_based"
    HIERARCHICAL = "hierarchical"
    ADAPTIVE = "adaptive"

@dataclass
class ContextGroup:
    """Thông tin về một context group"""
    group_id: int
    blocks: List
    context_type: str  # 'dialogue', 'narrative', 'description', 'mixed'
    semantic_score: float
    character_voices: List[str] = None
    translation_style: str = None

@dataclass
class TranslationContext:
    """Context cho translation"""
    previous_blocks: List = None
    character_voices: Dict[str, str] = None
    translation_style: str = None
    context_window: int = 5
    
    def __post_init__(self):
        if self.previous_blocks is None:
            self.previous_blocks = []
        if self.character_voices is None:
            self.character_voices = {}

class ContextAwareTranslator:
    """
    Context-aware translator với multiple strategies
    """
    
    def __init__(self, block_manager, logger=None):
        self.block_manager = block_manager
        self.logger = logger
        self.context_strategy = ContextStrategy.SEMANTIC_GROUPING
        self.context_window_size = 5
        
        # Character voice patterns
        self.character_patterns = {
            'formal': ['sir', 'madam', 'please', 'thank you', 'excuse me'],
            'casual': ['hey', 'yo', 'dude', 'man', 'bro'],
            'rude': ['damn', 'shit', 'fuck', 'ass', 'bitch'],
            'polite': ['would you', 'could you', 'if you please', 'kindly'],
            'childish': ['wow', 'cool', 'awesome', 'amazing', 'super']
        }
    
    def set_logger(self, logger):
        self.logger = logger
    
    def _log(self, level: str, msg: str):
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(f"[{level.upper()}] {msg}")
    
    def translate_with_context(self, input_text: str, strategy: ContextStrategy = None) -> str:
        """
        Translate với context awareness
        """
        if strategy is None:
            strategy = self.context_strategy
        
        blocks_info = self.block_manager.extract_blocks_with_info(input_text)
        
        if strategy == ContextStrategy.SEMANTIC_GROUPING:
            return self._semantic_grouping_translation(blocks_info)
        elif strategy == ContextStrategy.WINDOW_BASED:
            return self._window_based_translation(blocks_info)
        elif strategy == ContextStrategy.HIERARCHICAL:
            return self._hierarchical_translation(blocks_info)
        elif strategy == ContextStrategy.ADAPTIVE:
            return self._adaptive_translation(blocks_info)
        else:
            return self._semantic_grouping_translation(blocks_info)
    
    def _semantic_grouping_translation(self, blocks_info: List) -> str:
        """Translate với semantic grouping"""
        self._log('info', f"🔍 Using semantic grouping translation for {len(blocks_info)} blocks")
        
        # Group blocks theo semantic similarity
        context_groups = self._create_semantic_groups(blocks_info)
        
        translated_blocks = []
        translation_context = TranslationContext()
        
        for group in context_groups:
            self._log('info', f"📊 Processing group {group.group_id} with {len(group.blocks)} blocks")
            
            # Update context với group info
            self._update_translation_context(translation_context, group)
            
            # Translate group với context
            group_text = self._blocks_to_text(group.blocks)
            translated_group = self._translate_group_with_context(group_text, translation_context)
            
            # Extract blocks từ translated group
            translated_group_blocks = self.block_manager.extract_blocks_with_info(translated_group)
            translated_blocks.extend(translated_group_blocks)
            
            # Update context cho next group
            translation_context.previous_blocks.extend(group.blocks)
        
        return self.block_manager._blocks_info_to_text(translated_blocks)
    
    def _window_based_translation(self, blocks_info: List) -> str:
        """Translate với context window"""
        self._log('info', f"🔍 Using window-based translation with window size {self.context_window_size}")
        
        translated_blocks = []
        translation_context = TranslationContext(context_window=self.context_window_size)
        
        for i in range(0, len(blocks_info), self.context_window_size):
            window_blocks = blocks_info[i:i + self.context_window_size]
            
            self._log('info', f"📊 Processing window {i//self.context_window_size + 1} with {len(window_blocks)} blocks")
            
            # Create context từ previous blocks
            context = self._create_context_from_previous(translation_context.previous_blocks)
            
            # Translate window với context
            window_text = self._blocks_to_text(window_blocks)
            translated_window = self._translate_with_context(window_text, context)
            
            # Extract blocks từ translated window
            translated_window_blocks = self.block_manager.extract_blocks_with_info(translated_window)
            translated_blocks.extend(translated_window_blocks)
            
            # Update context cho next window
            translation_context.previous_blocks.extend(window_blocks)
        
        return self.block_manager._blocks_info_to_text(translated_blocks)
    
    def _hierarchical_translation(self, blocks_info: List) -> str:
        """Translate với hierarchical approach"""
        self._log('info', f"🔍 Using hierarchical translation for {len(blocks_info)} blocks")
        
        # Create hierarchical structure
        hierarchy = self._create_hierarchy(blocks_info)
        
        translated_blocks = []
        
        for level in hierarchy:
            self._log('info', f"📊 Processing hierarchy level with {len(level)} groups")
            
            for group in level:
                # Translate group với parent context
                group_text = self._blocks_to_text(group.blocks)
                translated_group = self._translate_hierarchical_group(group_text, group)
                
                # Extract blocks
                translated_group_blocks = self.block_manager.extract_blocks_with_info(translated_group)
                translated_blocks.extend(translated_group_blocks)
        
        return self.block_manager._blocks_info_to_text(translated_blocks)
    
    def _adaptive_translation(self, blocks_info: List) -> str:
        """Adaptive translation dựa trên content analysis"""
        self._log('info', f"🔍 Using adaptive translation for {len(blocks_info)} blocks")
        
        # Analyze content để chọn strategy phù hợp
        content_analysis = self._analyze_content(blocks_info)
        
        if content_analysis['has_dialogue'] and content_analysis['has_narrative']:
            strategy = ContextStrategy.SEMANTIC_GROUPING
        elif content_analysis['is_long_text']:
            strategy = ContextStrategy.WINDOW_BASED
        elif content_analysis['has_hierarchy']:
            strategy = ContextStrategy.HIERARCHICAL
        else:
            strategy = ContextStrategy.SEMANTIC_GROUPING
        
        self._log('info', f"📊 Adaptive strategy selected: {strategy.value}")
        
        return self.translate_with_context(self.block_manager._blocks_info_to_text(blocks_info), strategy)
    
    def _create_semantic_groups(self, blocks_info: List) -> List[ContextGroup]:
        """Create semantic groups từ blocks"""
        groups = []
        current_group = []
        group_id = 1
        
        for i, block in enumerate(blocks_info):
            if current_group and not self._is_semantically_related(block, current_group[-1]):
                # Create group từ current blocks
                group = self._create_context_group(group_id, current_group)
                groups.append(group)
                group_id += 1
                current_group = [block]
            else:
                current_group.append(block)
        
        # Add final group
        if current_group:
            group = self._create_context_group(group_id, current_group)
            groups.append(group)
        
        return groups
    
    def _is_semantically_related(self, block1, block2) -> bool:
        """Check semantic relationship giữa 2 blocks"""
        # Analyze content similarity
        content1 = block1.content.lower()
        content2 = block2.content.lower()
        
        # Check character voices
        voice1 = self._detect_character_voice(content1)
        voice2 = self._detect_character_voice(content2)
        
        if voice1 and voice2 and voice1 == voice2:
            return True
        
        # Check content type
        type1 = self._detect_content_type(content1)
        type2 = self._detect_content_type(content2)
        
        if type1 == type2:
            return True
        
        # Check content length similarity
        len1 = len(content1)
        len2 = len(content2)
        
        if min(len1, len2) > 0:
            ratio = max(len1, len2) / min(len1, len2)
            if ratio < 3.0:  # Similar length
                return True
        
        return False
    
    def _detect_character_voice(self, content: str) -> Optional[str]:
        """Detect character voice từ content"""
        content_lower = content.lower()
        
        for voice, patterns in self.character_patterns.items():
            if any(pattern in content_lower for pattern in patterns):
                return voice
        
        return None
    
    def _detect_content_type(self, content: str) -> str:
        """Detect content type"""
        content_lower = content.lower()
        
        # Check for dialogue
        if '"' in content or "'" in content or any(word in content_lower for word in ['said', 'asked', 'replied']):
            return 'dialogue'
        
        # Check for narrative
        if any(word in content_lower for word in ['he', 'she', 'they', 'the', 'and', 'but']):
            return 'narrative'
        
        # Check for description
        if any(word in content_lower for word in ['was', 'were', 'is', 'are', 'looked', 'appeared']):
            return 'description'
        
        return 'mixed'
    
    def _create_context_group(self, group_id: int, blocks: List) -> ContextGroup:
        """Create context group từ blocks"""
        # Analyze group content
        group_content = " ".join([block.content for block in blocks])
        
        # Detect context type
        context_type = self._detect_content_type(group_content)
        
        # Calculate semantic score
        semantic_score = self._calculate_semantic_score(blocks)
        
        # Detect character voices
        character_voices = []
        for block in blocks:
            voice = self._detect_character_voice(block.content)
            if voice and voice not in character_voices:
                character_voices.append(voice)
        
        # Determine translation style
        translation_style = self._determine_translation_style(context_type, character_voices)
        
        return ContextGroup(
            group_id=group_id,
            blocks=blocks,
            context_type=context_type,
            semantic_score=semantic_score,
            character_voices=character_voices,
            translation_style=translation_style
        )
    
    def _calculate_semantic_score(self, blocks: List) -> float:
        """Calculate semantic similarity score cho group"""
        if len(blocks) <= 1:
            return 1.0
        
        # Simple heuristic: average content length similarity
        lengths = [len(block.content) for block in blocks]
        avg_length = sum(lengths) / len(lengths)
        
        # Calculate variance
        variance = sum((length - avg_length) ** 2 for length in lengths) / len(lengths)
        
        # Normalize score (lower variance = higher score)
        max_variance = max(lengths) ** 2
        score = 1.0 - (variance / max_variance) if max_variance > 0 else 1.0
        
        return max(0.0, min(1.0, score))
    
    def _determine_translation_style(self, context_type: str, character_voices: List[str]) -> str:
        """Determine translation style dựa trên context"""
        if 'rude' in character_voices:
            return 'vulgar'
        elif 'formal' in character_voices:
            return 'formal'
        elif 'casual' in character_voices:
            return 'casual'
        elif context_type == 'dialogue':
            return 'natural'
        elif context_type == 'narrative':
            return 'descriptive'
        else:
            return 'standard'
    
    def _update_translation_context(self, context: TranslationContext, group: ContextGroup):
        """Update translation context với group info"""
        # Update character voices
        for voice in group.character_voices:
            if voice not in context.character_voices:
                context.character_voices[voice] = voice
        
        # Update translation style
        if group.translation_style:
            context.translation_style = group.translation_style
    
    def _translate_group_with_context(self, group_text: str, context: TranslationContext) -> str:
        """Translate group với context"""
        # Create context-aware prompt
        prompt = self._create_context_aware_prompt(group_text, context)
        
        # For now, return the text as-is (will be replaced by actual translation)
        # In real implementation, this would call the translation service
        return group_text
    
    def _create_context_aware_prompt(self, text: str, context: TranslationContext) -> str:
        """Create context-aware prompt"""
        prompt = f"""
CONTEXT-AWARE TRANSLATION:

CONTEXT INFORMATION:
- Translation Style: {context.translation_style or 'standard'}
- Character Voices: {list(context.character_voices.keys())}
- Previous Context: {len(context.previous_blocks)} blocks

TRANSLATION RULES:
1. Maintain character voice consistency
2. Use appropriate translation style
3. Preserve context from previous blocks
4. Keep block structure intact

TEXT TO TRANSLATE:
{text}

TRANSLATE WITH CONTEXT AWARENESS:
"""
        return prompt
    
    def _blocks_to_text(self, blocks: List) -> str:
        """Convert blocks to text"""
        return "\n".join([block.content for block in blocks])
    
    def _create_context_from_previous(self, previous_blocks: List) -> str:
        """Create context từ previous blocks"""
        if not previous_blocks:
            return ""
        
        # Take last few blocks for context
        context_blocks = previous_blocks[-3:]  # Last 3 blocks
        context_text = self._blocks_to_text(context_blocks)
        
        return f"Previous context:\n{context_text}\n\n"
    
    def _translate_with_context(self, text: str, context: str) -> str:
        """Translate với context"""
        # For now, return the text as-is
        # In real implementation, this would call the translation service with context
        return text
    
    def _create_hierarchy(self, blocks_info: List) -> List[List[ContextGroup]]:
        """Create hierarchical structure"""
        # Simple hierarchy: group by content type first, then by semantic similarity
        content_groups = {}
        
        for block in blocks_info:
            content_type = self._detect_content_type(block.content)
            if content_type not in content_groups:
                content_groups[content_type] = []
            content_groups[content_type].append(block)
        
        # Create hierarchy levels
        hierarchy = []
        for content_type, blocks in content_groups.items():
            groups = self._create_semantic_groups(blocks)
            hierarchy.append(groups)
        
        return hierarchy
    
    def _translate_hierarchical_group(self, text: str, group: ContextGroup) -> str:
        """Translate hierarchical group"""
        # For now, return the text as-is
        return text
    
    def _analyze_content(self, blocks_info: List) -> Dict:
        """Analyze content để chọn strategy"""
        total_blocks = len(blocks_info)
        total_length = sum(len(block.content) for block in blocks_info)
        
        # Check for dialogue
        dialogue_blocks = 0
        for block in blocks_info:
            if self._detect_content_type(block.content) == 'dialogue':
                dialogue_blocks += 1
        
        # Check for narrative
        narrative_blocks = 0
        for block in blocks_info:
            if self._detect_content_type(block.content) == 'narrative':
                narrative_blocks += 1
        
        return {
            'total_blocks': total_blocks,
            'total_length': total_length,
            'is_long_text': total_length > 10000,
            'has_dialogue': dialogue_blocks > 0,
            'has_narrative': narrative_blocks > 0,
            'dialogue_ratio': dialogue_blocks / total_blocks if total_blocks > 0 else 0,
            'narrative_ratio': narrative_blocks / total_blocks if total_blocks > 0 else 0,
            'has_hierarchy': dialogue_blocks > 0 and narrative_blocks > 0
        }
