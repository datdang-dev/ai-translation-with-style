"""
@brief EnhancedPromptEngineer: Advanced prompt engineering với multiple strategies
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class PromptStrategy(Enum):
    STANDARD = "standard"
    STRUCTURED = "structured"
    MULTI_STAGE = "multi_stage"
    CONTEXT_AWARE = "context_aware"
    ERROR_PREVENTION = "error_prevention"

@dataclass
class PromptConfig:
    """Configuration cho prompt engineering"""
    strategy: PromptStrategy = PromptStrategy.STRUCTURED
    include_validation_rules: bool = True
    include_error_prevention: bool = True
    context_window_size: int = 5
    max_retries: int = 3
    confidence_threshold: float = 0.8

class EnhancedPromptEngineer:
    """
    Enhanced Prompt Engineer với multiple strategies để handle AI response issues
    """
    
    def __init__(self, block_manager, logger=None):
        self.block_manager = block_manager
        self.logger = logger
        self.config = PromptConfig()
    
    def set_logger(self, logger):
        self.logger = logger
    
    def _log(self, level: str, msg: str):
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(f"[{level.upper()}] {msg}")
    
    def create_enhanced_prompt(self, input_text: str, strategy: PromptStrategy = None) -> str:
        """
        Tạo enhanced prompt dựa trên strategy
        """
        if strategy is None:
            strategy = self.config.strategy
        
        if strategy == PromptStrategy.STRUCTURED:
            return self._create_structured_prompt(input_text)
        elif strategy == PromptStrategy.MULTI_STAGE:
            return self._create_multi_stage_prompt(input_text)
        elif strategy == PromptStrategy.CONTEXT_AWARE:
            return self._create_context_aware_prompt(input_text)
        elif strategy == PromptStrategy.ERROR_PREVENTION:
            return self._create_error_prevention_prompt(input_text)
        else:
            return self._create_standard_prompt(input_text)
    
    def _create_structured_prompt(self, input_text: str) -> str:
        """Tạo structured prompt với validation rules rõ ràng"""
        blocks_info = self.block_manager.extract_blocks_with_info(input_text)
        duplicates = self.block_manager.find_duplicate_block_ids(blocks_info)
        
        prompt = f"""
######### BLOCK INPUT INFORMATION #########:
   - Number of blocks: {len(blocks_info)}
   - Detail block ids: {[block.id for block in blocks_info]}

Now follow the exact same format and style for all future translations and translate the text in the triple backticks block below:

```
{input_text}
```

CRITICAL TRANSLATION RULES FOR YOUR RESPONSE - MUST FOLLOW:

1. OUTPUT REQUIREMENTS:
   - MUST return EXACTLY {len(blocks_info)} blocks
   - MUST preserve ALL block IDs in order
   - MUST translate ALL content within blocks
   - NO skipping, merging, or reordering blocks

2. VALIDATION CHECKLIST FOR OUTPUT:
   □ All {len(blocks_info)} blocks present
   □ All block IDs preserved
   □ No extra blocks added
   □ No blocks skipped

3. ERROR PREVENTION:
   - If unsure about translation, use placeholder: [NEEDS_REVIEW]
   - If block seems empty, keep structure: [EMPTY_BLOCK]
   - Never skip blocks even if content seems irrelevant
"""
        return prompt
    
    def _create_multi_stage_prompt(self, input_text: str) -> List[str]:
        """Tạo multi-stage prompts để handle complex cases"""
        blocks_info = self.block_manager.extract_blocks_with_info(input_text)
        duplicates = self.block_manager.find_duplicate_block_ids(blocks_info)
        
        stages = []
        
        # Stage 1: Structure analysis
        stage1 = f"""
ANALYZE STRUCTURE FIRST:
Count blocks and identify any issues in the input text.

Input text:
{input_text}

Respond with this exact format:
- Total blocks: [number]
- Block IDs: [list]
- Issues found: [list]
- Duplicate IDs: [list]
"""
        stages.append(stage1)
        
        # Stage 2: Translation with validation
        stage2 = f"""
NOW TRANSLATE WITH VALIDATION:
Based on the analysis, translate the following text ensuring:
1. Block count matches: {len(blocks_info)}
2. All IDs preserved: {[block.id for block in blocks_info]}
3. No content lost
4. Handle duplicates carefully: {list(duplicates.keys()) if duplicates else 'None'}

Input text:
{input_text}

After translation, verify:
1. Block count matches
2. All IDs preserved
3. No content lost
"""
        stages.append(stage2)
        
        return stages
    
    def _create_context_aware_prompt(self, input_text: str) -> str:
        """Tạo context-aware prompt"""
        blocks_info = self.block_manager.extract_blocks_with_info(input_text)
        
        # Group blocks theo semantic similarity
        groups = self._semantic_block_grouping(blocks_info)
        
        prompt = f"""
CONTEXT-AWARE TRANSLATION:
Translate the following text while maintaining context consistency across related blocks.

STRUCTURE ANALYSIS:
- Total blocks: {len(blocks_info)}
- Semantic groups: {len(groups)}
- Block IDs: {[block.id for block in blocks_info]}

CONTEXT GROUPS:
{self._format_context_groups(groups)}

TRANSLATION RULES:
1. Maintain context consistency within each group
2. Preserve all block IDs and structure
3. Ensure smooth transitions between groups
4. Keep character voices consistent

INPUT TEXT:

```
{input_text}
```

NOW RE-TRANSLATE WITH CONTEXT AWARENESS:
"""
        return prompt
    
    def _create_error_prevention_prompt(self, input_text: str) -> str:
        """Tạo prompt với error prevention focus"""
        blocks_info = self.block_manager.extract_blocks_with_info(input_text)
        duplicates = self.block_manager.find_duplicate_block_ids(blocks_info)
        
        prompt = f"""
ERROR PREVENTION TRANSLATION:
This input has potential issues that need careful handling.

POTENTIAL ISSUES:
- Duplicate block IDs: {list(duplicates.keys()) if duplicates else 'None'}
- Total blocks: {len(blocks_info)}
- Complex structure detected

PREVENTION STRATEGIES:
1. COUNT CAREFULLY: Ensure exactly {len(blocks_info)} blocks in output
2. HANDLE DUPLICATES: Each duplicate ID should appear the same number of times
3. PRESERVE ORDER: Maintain exact block order
4. NO SKIPPING: Translate every block, even if content seems irrelevant
5. USE PLACEHOLDERS: If unsure, use [NEEDS_REVIEW] instead of skipping

BLOCK IDS TO PRESERVE:
{[block.id for block in blocks_info]}

INPUT TEXT:

```
{input_text}
```

NOW RE-TRANSLATE WITH ERROR PREVENTION:
"""
        return prompt
    
    def _create_standard_prompt(self, input_text: str) -> str:
        """Tạo standard prompt với basic validation"""
        blocks_info = self.block_manager.extract_blocks_with_info(input_text)
        
        prompt = f"""
TRANSLATE THE FOLLOWING TEXT:
- Preserve all block IDs: {[block.id for block in blocks_info]}
- Maintain block count: {len(blocks_info)}
- Translate all content

INPUT:
{input_text}
"""
        return prompt
    
    def _semantic_block_grouping(self, blocks_info: List) -> List[List]:
        """Group blocks theo semantic similarity"""
        groups = []
        current_group = []
        
        for i, block in enumerate(blocks_info):
            # Simple grouping: group consecutive blocks with similar content length
            if current_group and self._is_semantically_related(block, current_group[-1]):
                current_group.append(block)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [block]
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _is_semantically_related(self, block1, block2) -> bool:
        """Check if two blocks are semantically related"""
        # Simple heuristic: similar content length and structure
        len1 = len(block1.content)
        len2 = len(block2.content)
        
        # If content lengths are similar (within 50% difference)
        if min(len1, len2) > 0:
            ratio = max(len1, len2) / min(len1, len2)
            return ratio < 2.0
        
        return True
    
    def _format_context_groups(self, groups: List[List]) -> str:
        """Format context groups cho prompt"""
        formatted = []
        for i, group in enumerate(groups):
            group_info = f"Group {i+1}: {len(group)} blocks"
            block_ids = [block.id for block in group]
            formatted.append(f"  {group_info} - IDs: {block_ids}")
        
        return "\n".join(formatted)
    
    def create_adaptive_prompt(self, input_text: str, previous_errors: List[str] = None) -> str:
        """Tạo adaptive prompt dựa trên previous errors"""
        if not previous_errors:
            return self._create_structured_prompt(input_text)
        
        # Analyze previous errors để tạo targeted prompt
        error_patterns = self._analyze_error_patterns(previous_errors)
        
        if 'missing_blocks' in error_patterns:
            return self._create_missing_blocks_prompt(input_text)
        elif 'duplicate_issues' in error_patterns:
            return self._create_duplicate_handling_prompt(input_text)
        elif 'structure_issues' in error_patterns:
            return self._create_structure_fix_prompt(input_text)
        else:
            return self._create_error_prevention_prompt(input_text)
    
    def _analyze_error_patterns(self, errors: List[str]) -> List[str]:
        """Analyze error patterns từ previous attempts"""
        patterns = []
        
        for error in errors:
            error_lower = error.lower()
            if 'missing' in error_lower or 'block' in error_lower:
                patterns.append('missing_blocks')
            elif 'duplicate' in error_lower:
                patterns.append('duplicate_issues')
            elif 'structure' in error_lower or 'format' in error_lower:
                patterns.append('structure_issues')
        
        return list(set(patterns))
    
    def _create_missing_blocks_prompt(self, input_text: str) -> str:
        """Tạo prompt đặc biệt cho missing blocks issue"""
        blocks_info = self.block_manager.extract_blocks_with_info(input_text)
        
        prompt = f"""
CRITICAL: PREVIOUS ATTEMPTS MISSED BLOCKS
You MUST ensure ALL {len(blocks_info)} blocks are translated.

BLOCK COUNTING EXERCISE:
1. Count the blocks in input: {len(blocks_info)}
2. Ensure output has exactly {len(blocks_info)} blocks
3. Check each block ID: {[block.id for block in blocks_info]}

MISSING BLOCKS PREVENTION:
- Translate EVERY block, no exceptions
- If content seems irrelevant, still translate it
- Use [EMPTY] for truly empty blocks
- Double-check block count before finishing

INPUT TEXT:

```
{input_text}
```

NOW RE-TRANSLATE ALL BLOCKS:
"""
        return prompt
    
    def _create_duplicate_handling_prompt(self, input_text: str) -> str:
        """Tạo prompt đặc biệt cho duplicate handling"""
        blocks_info = self.block_manager.extract_blocks_with_info(input_text)
        duplicates = self.block_manager.find_duplicate_block_ids(blocks_info)
        
        prompt = f"""
CRITICAL: HANDLE DUPLICATE BLOCK IDs
This input contains duplicate block IDs that must be handled carefully.

DUPLICATE IDs: {list(duplicates.keys())}

DUPLICATE HANDLING RULES:
1. Each duplicate ID should appear the same number of times in output
2. Translate each occurrence separately
3. Maintain the order of duplicate blocks
4. Don't merge or skip duplicate blocks

BLOCK STRUCTURE:
- Total blocks: {len(blocks_info)}
- Unique IDs: {len(set(block.id for block in blocks_info))}
- Duplicate IDs: {len(duplicates)}

INPUT TEXT:

```
{input_text}
```

NOW RE-TRANSLATE WITH DUPLICATE AWARENESS:
"""
        return prompt
    
    def _create_structure_fix_prompt(self, input_text: str) -> str:
        """Tạo prompt đặc biệt cho structure issues"""
        blocks_info = self.block_manager.extract_blocks_with_info(input_text)
        
        prompt = f"""
CRITICAL: MAINTAIN EXACT STRUCTURE
Previous attempts had structure issues. Maintain exact block structure.

STRUCTURE REQUIREMENTS:
- Block count: {len(blocks_info)}
- Block order: {[block.id for block in blocks_info]}
- No reordering, no merging, no splitting

STRUCTURE VALIDATION:
1. Count blocks in output
2. Verify block IDs match input
3. Check block order
4. Ensure no extra or missing blocks

INPUT TEXT:

```
{input_text}
```

NOW RE-TRANSLATE WITH STRUCTURE FOCUS:
"""
        return prompt
