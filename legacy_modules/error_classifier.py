"""
@brief ErrorClassifier: Classify errors và apply recovery strategies
"""
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import re

class ErrorType(Enum):
    MISSING_BLOCKS = "missing_blocks"
    DUPLICATE_OUTPUT = "duplicate_output"
    MISMATCHED_IDS = "mismatched_ids"
    STRUCTURE_ISSUES = "structure_issues"
    CONTENT_ISSUES = "content_issues"
    WARNING_LEVEL = "warning_level"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class ErrorInfo:
    """Thông tin chi tiết về error"""
    error_type: ErrorType
    severity: str  # 'critical', 'warning', 'info'
    description: str
    affected_blocks: List[str] = None
    suggested_fix: str = None
    confidence: float = 0.0

class RecoveryStrategy:
    """Base class cho recovery strategies"""
    
    def __init__(self, block_manager, logger=None):
        self.block_manager = block_manager
        self.logger = logger
    
    def can_handle(self, error_info: ErrorInfo) -> bool:
        """Check if strategy can handle this error"""
        raise NotImplementedError
    
    def apply(self, input_text: str, output_text: str, error_info: ErrorInfo) -> Tuple[str, bool]:
        """Apply recovery strategy"""
        raise NotImplementedError

class MissingBlocksRecovery(RecoveryStrategy):
    """Recovery strategy cho missing blocks"""
    
    def can_handle(self, error_info: ErrorInfo) -> bool:
        return error_info.error_type == ErrorType.MISSING_BLOCKS
    
    def apply(self, input_text: str, output_text: str, error_info: ErrorInfo) -> Tuple[str, bool]:
        """Recover missing blocks"""
        if self.logger:
            self.logger.info(f"🔄 Applying missing blocks recovery...")
        
        input_blocks = self.block_manager.extract_blocks_with_info(input_text)
        output_blocks = self.block_manager.extract_blocks_with_info(output_text)
        
        # Tìm missing blocks
        missing_blocks = self.block_manager.find_missing_blocks_by_id(input_blocks, output_blocks)
        
        if not missing_blocks:
            return output_text, False
        
        # Group missing blocks theo context để translate hiệu quả hơn
        grouped_missing = self._group_missing_blocks(missing_blocks)
        
        # Tạo text cho missing blocks
        missing_text = self._create_missing_blocks_text(grouped_missing)
        
        if self.logger:
            self.logger.info(f"📊 Missing blocks grouped into {len(grouped_missing)} groups")
        
        return missing_text, True
    
    def _group_missing_blocks(self, missing_blocks: List) -> List[List]:
        """Group missing blocks theo context"""
        if len(missing_blocks) <= 3:
            return [missing_blocks]  # Không cần group nếu ít blocks
        
        groups = []
        current_group = []
        
        for block in missing_blocks:
            if len(current_group) < 3:  # Max 3 blocks per group
                current_group.append(block)
            else:
                groups.append(current_group)
                current_group = [block]
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _create_missing_blocks_text(self, grouped_missing: List[List]) -> str:
        """Tạo text cho missing blocks"""
        texts = []
        
        for group in grouped_missing:
            group_text = "\n\n".join([block.content for block in group])
            texts.append(group_text)
        
        return "\n\n---MISSING_BLOCKS_SEPARATOR---\n\n".join(texts)

class DuplicateOutputRecovery(RecoveryStrategy):
    """Recovery strategy cho duplicate output issues"""
    
    def can_handle(self, error_info: ErrorInfo) -> bool:
        return error_info.error_type == ErrorType.DUPLICATE_OUTPUT
    
    def apply(self, input_text: str, output_text: str, error_info: ErrorInfo) -> Tuple[str, bool]:
        """Fix duplicate output issues"""
        if self.logger:
            self.logger.info(f"🔄 Applying duplicate output recovery...")
        
        input_blocks = self.block_manager.extract_blocks_with_info(input_text)
        output_blocks = self.block_manager.extract_blocks_with_info(output_text)
        
        # Tìm duplicate IDs trong output
        output_duplicates = self.block_manager.find_duplicate_block_ids(output_blocks)
        
        if not output_duplicates:
            return output_text, False
        
        # Fix bằng cách giữ lại block đầu tiên của mỗi duplicate ID
        fixed_blocks = self._fix_duplicate_blocks(output_blocks, output_duplicates)
        
        # Tạo output mới
        fixed_output = self.block_manager._blocks_info_to_text(fixed_blocks)
        
        if self.logger:
            self.logger.info(f"🔧 Fixed {len(output_duplicates)} duplicate ID issues")
        
        return fixed_output, True
    
    def _fix_duplicate_blocks(self, output_blocks: List, duplicates: Dict) -> List:
        """Fix duplicate blocks bằng cách giữ lại block đầu tiên"""
        seen_ids = set()
        fixed_blocks = []
        
        for block in output_blocks:
            if block.id not in seen_ids:
                fixed_blocks.append(block)
                seen_ids.add(block.id)
            else:
                # Skip duplicate blocks
                continue
        
        return fixed_blocks

class StructureIssuesRecovery(RecoveryStrategy):
    """Recovery strategy cho structure issues"""
    
    def can_handle(self, error_info: ErrorInfo) -> bool:
        return error_info.error_type == ErrorType.STRUCTURE_ISSUES
    
    def apply(self, input_text: str, output_text: str, error_info: ErrorInfo) -> Tuple[str, bool]:
        """Fix structure issues"""
        if self.logger:
            self.logger.info(f"🔄 Applying structure issues recovery...")
        
        input_blocks = self.block_manager.extract_blocks_with_info(input_text)
        output_blocks = self.block_manager.extract_blocks_with_info(output_text)
        
        # Reconstruct output theo input structure
        reconstructed_blocks = self._reconstruct_structure(input_blocks, output_blocks)
        
        # Tạo output mới
        reconstructed_output = self.block_manager._blocks_info_to_text(reconstructed_blocks)
        
        if self.logger:
            self.logger.info(f"🔧 Reconstructed structure with {len(reconstructed_blocks)} blocks")
        
        return reconstructed_output, True
    
    def _reconstruct_structure(self, input_blocks: List, output_blocks: List) -> List:
        """Reconstruct output structure theo input"""
        output_by_id = {block.id: block for block in output_blocks}
        reconstructed = []
        
        for input_block in input_blocks:
            if input_block.id in output_by_id:
                # Use translated content
                reconstructed.append(output_by_id[input_block.id])
            else:
                # Keep original content for missing blocks
                reconstructed.append(input_block)
        
        return reconstructed

class ErrorClassifier:
    """
    Classify errors và apply recovery strategies
    """
    
    def __init__(self, block_manager, logger=None):
        self.block_manager = block_manager
        self.logger = logger
        
        # Initialize recovery strategies
        self.recovery_strategies = [
            MissingBlocksRecovery(block_manager, logger),
            DuplicateOutputRecovery(block_manager, logger),
            StructureIssuesRecovery(block_manager, logger)
        ]
    
    def set_logger(self, logger):
        self.logger = logger
        for strategy in self.recovery_strategies:
            strategy.logger = logger
    
    def _log(self, level: str, msg: str):
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(f"[{level.upper()}] {msg}")
    
    def classify_error(self, input_text: str, output_text: str) -> ErrorInfo:
        """Classify error type và severity"""
        input_blocks = self.block_manager.extract_blocks_with_info(input_text)
        output_blocks = self.block_manager.extract_blocks_with_info(output_text)

        validation = self.block_manager.validate_block_consistency(input_blocks, output_blocks)

        # Treat any non-empty missing_blocks (IDs or objects) as missing block error
        missing_blocks = validation.get('missing_blocks', [])
        # Accept both block objects and block IDs robustly
        if missing_blocks and len(missing_blocks) > 0:
            # If block objects, convert to IDs for affected_blocks
            if hasattr(missing_blocks[0], 'id'):
                affected_blocks = [b.id for b in missing_blocks]
            else:
                affected_blocks = missing_blocks
            return ErrorInfo(
                error_type=ErrorType.MISSING_BLOCKS,
                severity='critical',
                description=f"Missing {len(missing_blocks)} blocks",
                affected_blocks=affected_blocks,
                suggested_fix="Translate missing blocks separately",
                confidence=0.9
            )

        elif validation.get('duplicate_output_ids', []):
            return ErrorInfo(
                error_type=ErrorType.DUPLICATE_OUTPUT,
                severity='warning',
                description=f"Output has {len(validation['duplicate_output_ids'])} duplicate IDs",
                affected_blocks=validation['duplicate_output_ids'],
                suggested_fix="Remove duplicate blocks",
                confidence=0.8
            )

        elif validation.get('mismatched_ids', []):
            return ErrorInfo(
                error_type=ErrorType.MISMATCHED_IDS,
                severity='warning',
                description=f"Output has {len(validation['mismatched_ids'])} mismatched IDs",
                affected_blocks=validation['mismatched_ids'],
                suggested_fix="Fix block ID mapping",
                confidence=0.7
            )

        elif validation.get('warnings', []):
            return ErrorInfo(
                error_type=ErrorType.WARNING_LEVEL,
                severity='info',
                description=f"Output has {len(validation['warnings'])} warnings",
                suggested_fix="Review warnings",
                confidence=0.5
            )

        else:
            return ErrorInfo(
                error_type=ErrorType.UNKNOWN_ERROR,
                severity='info',
                description="Unknown error type",
                suggested_fix="Manual review required",
                confidence=0.3
            )
    
    def get_recovery_strategy(self, error_info: ErrorInfo) -> Optional[RecoveryStrategy]:
        """Get recovery strategy phù hợp cho error type"""
        for strategy in self.recovery_strategies:
            if strategy.can_handle(error_info):
                return strategy
        
        return None
    
    def apply_recovery(self, input_text: str, output_text: str, error_info: ErrorInfo) -> Tuple[str, bool]:
        """Apply recovery strategy cho error"""
        strategy = self.get_recovery_strategy(error_info)
        
        if not strategy:
            self._log('warning', f"No recovery strategy found for error type: {error_info.error_type}")
            return output_text, False
        
        try:
            recovered_text, success = strategy.apply(input_text, output_text, error_info)
            
            if success:
                self._log('info', f"✅ Successfully applied {strategy.__class__.__name__}")
            else:
                self._log('warning', f"⚠️ Recovery strategy {strategy.__class__.__name__} did not succeed")
            
            return recovered_text, success
            
        except Exception as e:
            self._log('error', f"❌ Recovery strategy failed: {e}")
            return output_text, False
    
    def analyze_error_patterns(self, errors: List[str]) -> Dict[str, int]:
        """Analyze error patterns từ previous attempts"""
        patterns = {
            'missing_blocks': 0,
            'duplicate_issues': 0,
            'structure_issues': 0,
            'content_issues': 0,
            'unknown': 0
        }
        
        for error in errors:
            error_lower = error.lower()
            
            if any(keyword in error_lower for keyword in ['missing', 'block', 'thiếu']):
                patterns['missing_blocks'] += 1
            elif any(keyword in error_lower for keyword in ['duplicate', 'trùng lặp']):
                patterns['duplicate_issues'] += 1
            elif any(keyword in error_lower for keyword in ['structure', 'format', 'cấu trúc']):
                patterns['structure_issues'] += 1
            elif any(keyword in error_lower for keyword in ['content', 'nội dung']):
                patterns['content_issues'] += 1
            else:
                patterns['unknown'] += 1
        
        return patterns
    
    def get_error_summary(self, input_text: str, output_text: str) -> Dict:
        """Get comprehensive error summary"""
        error_info = self.classify_error(input_text, output_text)
        strategy = self.get_recovery_strategy(error_info)
        
        return {
            'error_type': error_info.error_type.value,
            'severity': error_info.severity,
            'description': error_info.description,
            'affected_blocks': error_info.affected_blocks,
            'suggested_fix': error_info.suggested_fix,
            'confidence': error_info.confidence,
            'has_recovery_strategy': strategy is not None,
            'recovery_strategy_name': strategy.__class__.__name__ if strategy else None
        }
