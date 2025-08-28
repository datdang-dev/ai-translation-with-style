"""
@brief RealTimeValidator: Validate response trong khi stream để detect issues sớm
"""
from typing import Dict, List, Tuple, Optional, Generator
from dataclasses import dataclass
from enum import Enum
import re
import time

class ValidationState(Enum):
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    """Kết quả validation"""
    state: ValidationState
    message: str
    confidence: float
    suggestions: List[str] = None
    should_stop: bool = False

@dataclass
class StreamValidationState:
    """State tracking cho stream validation"""
    blocks_found: int = 0
    expected_blocks: int = 0
    missing_ids: set = None
    duplicate_ids: set = None
    current_block: str = None
    issues_detected: List[str] = None
    last_block_time: float = 0
    stream_start_time: float = 0
    
    def __post_init__(self):
        if self.missing_ids is None:
            self.missing_ids = set()
        if self.duplicate_ids is None:
            self.duplicate_ids = set()
        if self.issues_detected is None:
            self.issues_detected = []
        if self.stream_start_time == 0:
            self.stream_start_time = time.time()

class RealTimeValidator:
    """
    Real-time validator để detect issues trong khi stream response
    """
    
    def __init__(self, block_manager, logger=None):
        self.block_manager = block_manager
        self.logger = logger
        self.validation_state = StreamValidationState()
        
        # Configuration
        self.max_block_time = 30.0  # seconds
        self.max_stream_time = 300.0  # seconds
        self.min_blocks_ratio = 0.8  # minimum ratio of expected blocks
    
    def set_logger(self, logger):
        self.logger = logger
    
    def _log(self, level: str, msg: str):
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(f"[{level.upper()}] {msg}")
    
    def initialize_validation(self, input_text: str):
        """Initialize validation state cho input text"""
        input_blocks = self.block_manager.extract_blocks_with_info(input_text)
        self.validation_state.expected_blocks = len(input_blocks)
        self.validation_state.stream_start_time = time.time()
        self.validation_state.last_block_time = time.time()
        
        self._log('info', f"🔍 Initialized validation for {len(input_blocks)} expected blocks")
    
    def validate_stream_chunk(self, chunk: str) -> ValidationResult:
        """Validate một chunk của stream response"""
        current_time = time.time()
        
        # Update last block time
        self.validation_state.last_block_time = current_time
        
        # Check for block headers in chunk
        block_headers = self._extract_block_headers(chunk)
        
        for header in block_headers:
            self._process_block_header(header)
        
        # Check for potential issues
        issues = self._check_potential_issues(current_time)
        
        if issues:
            return self._create_validation_result(issues)
        
        return ValidationResult(
            state=ValidationState.VALID,
            message="Stream progressing normally",
            confidence=0.9,
            should_stop=False
        )
    
    def _extract_block_headers(self, chunk: str) -> List[str]:
        """Extract block headers từ chunk"""
        headers = []
        lines = chunk.split('\n')
        
        for line in lines:
            if re.match(r'^\s*---------\d+\s*$', line.strip()):
                headers.append(line.strip())
        
        return headers
    
    def _process_block_header(self, header: str):
        """Process một block header"""
        self.validation_state.blocks_found += 1
        
        # Check for duplicates
        if header in self.validation_state.duplicate_ids:
            self.validation_state.issues_detected.append(f"Duplicate block ID: {header}")
        else:
            self.validation_state.duplicate_ids.add(header)
        
        self._log('debug', f"📊 Found block: {header} (total: {self.validation_state.blocks_found})")
    
    def _check_potential_issues(self, current_time: float) -> List[str]:
        """Check for potential issues trong stream"""
        issues = []
        
        # Check stream timeout
        stream_duration = current_time - self.validation_state.stream_start_time
        if stream_duration > self.max_stream_time:
            issues.append(f"Stream timeout: {stream_duration:.1f}s > {self.max_stream_time}s")
        
        # Check block timeout
        block_duration = current_time - self.validation_state.last_block_time
        if block_duration > self.max_block_time:
            issues.append(f"Block timeout: {block_duration:.1f}s > {self.max_block_time}s")
        
        # Check block progress
        if self.validation_state.expected_blocks > 0:
            progress_ratio = self.validation_state.blocks_found / self.validation_state.expected_blocks
            if progress_ratio < self.min_blocks_ratio and stream_duration > 60:
                issues.append(f"Slow progress: {progress_ratio:.1%} < {self.min_blocks_ratio:.1%}")
        
        # Check for too many blocks
        if self.validation_state.blocks_found > self.validation_state.expected_blocks * 1.5:
            issues.append(f"Too many blocks: {self.validation_state.blocks_found} > {self.validation_state.expected_blocks * 1.5}")
        
        return issues
    
    def _create_validation_result(self, issues: List[str]) -> ValidationResult:
        """Create validation result từ issues"""
        if any('timeout' in issue.lower() for issue in issues):
            state = ValidationState.CRITICAL
            should_stop = True
        elif any('duplicate' in issue.lower() for issue in issues):
            state = ValidationState.WARNING
            should_stop = False
        else:
            state = ValidationState.ERROR
            should_stop = False
        
        suggestions = self._generate_suggestions(issues)
        
        return ValidationResult(
            state=state,
            message=f"Detected {len(issues)} issues: {'; '.join(issues)}",
            confidence=0.7,
            suggestions=suggestions,
            should_stop=should_stop
        )
    
    def _generate_suggestions(self, issues: List[str]) -> List[str]:
        """Generate suggestions cho issues"""
        suggestions = []
        
        for issue in issues:
            if 'timeout' in issue.lower():
                suggestions.append("Consider retrying with shorter chunks")
            elif 'duplicate' in issue.lower():
                suggestions.append("Check for duplicate block handling")
            elif 'progress' in issue.lower():
                suggestions.append("Consider using more specific prompts")
            elif 'too many' in issue.lower():
                suggestions.append("Check block counting logic")
        
        return suggestions
    
    def get_validation_summary(self) -> Dict:
        """Get validation summary"""
        stream_duration = time.time() - self.validation_state.stream_start_time
        block_duration = time.time() - self.validation_state.last_block_time
        
        progress_ratio = 0
        if self.validation_state.expected_blocks > 0:
            progress_ratio = self.validation_state.blocks_found / self.validation_state.expected_blocks
        
        return {
            'blocks_found': self.validation_state.blocks_found,
            'expected_blocks': self.validation_state.expected_blocks,
            'progress_ratio': progress_ratio,
            'stream_duration': stream_duration,
            'block_duration': block_duration,
            'issues_detected': len(self.validation_state.issues_detected),
            'duplicate_ids': len(self.validation_state.duplicate_ids),
            'state': 'healthy' if not self.validation_state.issues_detected else 'issues_detected'
        }
    
    def should_trigger_correction(self) -> bool:
        """Check if should trigger correction"""
        # Trigger correction nếu có critical issues hoặc nhiều issues
        critical_issues = [issue for issue in self.validation_state.issues_detected 
                          if 'timeout' in issue.lower() or 'critical' in issue.lower()]
        
        return len(critical_issues) > 0 or len(self.validation_state.issues_detected) > 3
    
    def reset_validation_state(self):
        """Reset validation state"""
        self.validation_state = StreamValidationState()
        self._log('info', "🔄 Reset validation state")

class StreamResponseValidator:
    """
    Validator cho complete stream response
    """
    
    def __init__(self, block_manager, logger=None):
        self.block_manager = block_manager
        self.logger = logger
        self.real_time_validator = RealTimeValidator(block_manager, logger)
    
    def set_logger(self, logger):
        self.logger = logger
        self.real_time_validator.set_logger(logger)
    
    def validate_stream_response(self, input_text: str, response_stream: Generator) -> Tuple[str, Dict]:
        """
        Validate stream response trong real-time
        Returns: (validated_response, validation_info)
        """
        self.real_time_validator.initialize_validation(input_text)
        
        full_response = ""
        validation_results = []
        
        try:
            for chunk in response_stream:
                full_response += chunk
                
                # Validate chunk
                validation_result = self.real_time_validator.validate_stream_chunk(chunk)
                validation_results.append(validation_result)
                
                # Log validation result
                if validation_result.state != ValidationState.VALID:
                    self._log_validation_result(validation_result)
                
                # Check if should stop
                if validation_result.should_stop:
                    self._log('warning', f"🛑 Stopping stream due to: {validation_result.message}")
                    break
            
            # Get final validation summary
            validation_summary = self.real_time_validator.get_validation_summary()
            
            # Check if correction needed
            if self.real_time_validator.should_trigger_correction():
                validation_summary['needs_correction'] = True
                validation_summary['correction_reason'] = 'Stream validation issues detected'
            else:
                validation_summary['needs_correction'] = False
            
            return full_response, validation_summary
            
        except Exception as e:
            self._log('error', f"❌ Stream validation failed: {e}")
            validation_summary = {
                'error': str(e),
                'needs_correction': True,
                'correction_reason': 'Stream validation exception'
            }
            return full_response, validation_summary
    
    def _log_validation_result(self, result: ValidationResult):
        """Log validation result"""
        level_map = {
            ValidationState.VALID: 'debug',
            ValidationState.WARNING: 'warning',
            ValidationState.ERROR: 'error',
            ValidationState.CRITICAL: 'error'
        }
        
        level = level_map.get(result.state, 'info')
        self._log(level, f"🔍 {result.message}")
        
        if result.suggestions:
            for suggestion in result.suggestions:
                self._log('info', f"💡 Suggestion: {suggestion}")
    
    def _log(self, level: str, msg: str):
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(f"[{level.upper()}] {msg}")
    
    def validate_complete_response(self, input_text: str, output_text: str) -> Dict:
        """Validate complete response sau khi stream finished"""
        input_blocks = self.block_manager.extract_blocks_with_info(input_text)
        output_blocks = self.block_manager.extract_blocks_with_info(output_text)
        
        validation = self.block_manager.validate_block_consistency(input_blocks, output_blocks)
        
        # Add stream validation info
        stream_summary = self.real_time_validator.get_validation_summary()
        
        complete_validation = {
            'structure_validation': validation,
            'stream_validation': stream_summary,
            'overall_valid': validation['is_valid'] and not stream_summary.get('needs_correction', False),
            'total_issues': len(validation.get('errors', [])) + len(validation.get('warnings', [])) + len(stream_summary.get('issues_detected', []))
        }
        
        return complete_validation
