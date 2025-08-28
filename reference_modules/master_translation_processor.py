"""
@brief MasterTranslationProcessor: Master integration của tất cả enhanced components
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import time

from common_modules.enhanced_block_manager import EnhancedBlockManager
from .enhanced_prompt_engineer import EnhancedPromptEngineer, PromptStrategy
from .error_classifier import ErrorClassifier, ErrorType
from .real_time_validator import StreamResponseValidator
from .context_aware_translator import ContextAwareTranslator, ContextStrategy
from .quality_assurance import QualityAssurance

@dataclass
class ProcessingConfig:
    """Configuration cho master processor"""
    # Processing mode removed: defaults are tuned for enhanced behavior
    # (kept field name for backward compatibility but now treated as informational)
    mode: str = "enhanced"
    max_retries: int = 3
    enable_real_time_validation: bool = True
    enable_context_awareness: bool = True
    enable_quality_assurance: bool = True
    confidence_threshold: float = 0.8
    timeout_seconds: int = 300

@dataclass
class ProcessingResult:
    """Kết quả processing"""
    success: bool
    output_text: str
    processing_time: float
    retry_count: int
    quality_score: float
    confidence_level: str
    issues_detected: List[str]
    recommendations: List[str]
    error_summary: Dict = None

class MasterTranslationProcessor:
    """
    Master Translation Processor - Integrate tất cả enhanced components
    """
    
    def __init__(self, translator_service, logger=None):
        self.translator_service = translator_service
        self.logger = logger
        self.config = ProcessingConfig()
        
        # Initialize all components
        self.block_manager = EnhancedBlockManager()
        self.prompt_engineer = EnhancedPromptEngineer(self.block_manager, logger)
        self.error_classifier = ErrorClassifier(self.block_manager, logger)
        self.stream_validator = StreamResponseValidator(self.block_manager, logger)
        self.context_translator = ContextAwareTranslator(self.block_manager, logger)
        self.quality_assurance = QualityAssurance(self.block_manager, logger)
        
        # Set loggers
        self._set_component_loggers()
    
    def _set_component_loggers(self):
        """Set logger cho tất cả components"""
        components = [
            self.block_manager,
            self.prompt_engineer,
            self.error_classifier,
            self.stream_validator,
            self.context_translator,
            self.quality_assurance
        ]
        
        for component in components:
            if hasattr(component, 'set_logger'):
                component.set_logger(self.logger)
    
    def set_logger(self, logger):
        self.logger = logger
        self._set_component_loggers()
    
    def _log(self, level: str, msg: str):
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(f"[{level.upper()}] {msg}")
    
    def process_file(self, input_text: str, output_path: str, config: ProcessingConfig = None) -> ProcessingResult:
        """
        Process file với master integration
        """
        if config is None:
            config = self.config

        start_time = time.time()
        retry_count = 0
        issues_detected: List[str] = []
        recommendations: List[str] = []

        self._log('info', f"🚀 Starting master translation processing (mode: {config.mode})")

        # Analyze input
        input_analysis = self._analyze_input(input_text)
        self._log('info', f"📊 Input analysis: {input_analysis['total_blocks']} blocks, {input_analysis['duplicate_ids']} duplicate IDs")

        while retry_count < config.max_retries:
            try:
                self._log('info', f"🔄 Processing attempt {retry_count + 1}/{config.max_retries}")

                # Step 1: Create enhanced prompt
                prompt = self._create_enhanced_prompt(input_text, retry_count, issues_detected)

                # Step 2: Translate with real-time validation
                if config.enable_real_time_validation:
                    output_text, stream_validation = self._translate_with_real_time_validation(input_text, prompt)
                else:
                    output_text = self.translator_service.translate_text(prompt)
                    stream_validation = {'needs_correction': False}

                # Step 3: Error classification and recovery
                error_info = self.error_classifier.classify_error(input_text, output_text)
                if error_info.error_type != ErrorType.UNKNOWN_ERROR:
                    self._log('warning', f"⚠️ Error detected: {error_info.description}")
                    issues_detected.append(error_info.description)

                    recovered_text, recovery_success = self.error_classifier.apply_recovery(input_text, output_text, error_info)
                    if recovery_success:
                        output_text = recovered_text
                        self._log('info', "✅ Recovery successful")
                    else:
                        self._log('warning', "⚠️ Recovery failed")

                # Step 4: Context-aware processing (if enabled)
                if config.enable_context_awareness and self._should_apply_context_awareness(input_analysis):
                    self._log('info', "🔍 Applying context-aware processing")
                    output_text = self.context_translator.translate_with_context(output_text)

                # Step 5: Quality assurance (if enabled)
                quality_score = 0.0
                confidence_level = "unknown"
                if config.enable_quality_assurance:
                    quality_report = self.quality_assurance.validate_translation(input_text, output_text)
                    quality_score = getattr(quality_report, 'overall_score', 0.0)
                    confidence_level = getattr(quality_report, 'confidence_level', 'unknown')

                    if getattr(quality_report, 'critical_issues', None):
                        issues_detected.extend(quality_report.critical_issues)

                    if getattr(quality_report, 'recommendations', None):
                        recommendations.extend(quality_report.recommendations)

                    self._log('info', f"📊 Quality score: {quality_score:.2f} ({confidence_level})")

                # Step 6: Final validation
                final_validation = self._final_validation(input_text, output_text)
                if final_validation.get('is_valid'):
                    processing_time = time.time() - start_time

                    # Write output
                    self._write_output(output_text, output_path)

                    result = ProcessingResult(
                        success=True,
                        output_text=output_text,
                        processing_time=processing_time,
                        retry_count=retry_count + 1,
                        quality_score=quality_score,
                        confidence_level=confidence_level,
                        issues_detected=issues_detected,
                        recommendations=recommendations,
                        error_summary=final_validation
                    )

                    self._log('info', f"✅ Master processing completed successfully in {processing_time:.2f}s")
                    return result
                else:
                    issues_detected.extend(final_validation.get('errors', []))
                    self._log('warning', f"⚠️ Final validation failed: {final_validation.get('errors', [])}")

            except Exception as e:
                self._log('error', f"❌ Processing attempt {retry_count + 1} failed: {e}")
                issues_detected.append(f"Processing error: {e}")

            retry_count += 1
            if retry_count < config.max_retries:
                self._log('info', "🔄 Retrying in 2 seconds...")
                time.sleep(2)

        # All retries failed
        processing_time = time.time() - start_time

        result = ProcessingResult(
            success=False,
            output_text="",
            processing_time=processing_time,
            retry_count=retry_count,
            quality_score=0.0,
            confidence_level="failed",
            issues_detected=issues_detected,
            recommendations=recommendations
        )

        self._log('error', f"❌ Master processing failed after {retry_count} attempts")
        return result
    
    def _analyze_input(self, input_text: str) -> Dict:
        """Analyze input text"""
        blocks_info = self.block_manager.extract_blocks_with_info(input_text)
        duplicates = self.block_manager.find_duplicate_block_ids(blocks_info)
        
        return {
            'total_blocks': len(blocks_info),
            'duplicate_ids': len(duplicates),
            'duplicate_details': list(duplicates.keys()),
            'has_issues': len(duplicates) > 0
        }
    
    def _create_enhanced_prompt(self, input_text: str, retry_count: int, previous_issues: List[str]) -> str:
        """Create enhanced prompt dựa trên retry count và previous issues"""
        if retry_count == 0:
            # First attempt: use structured prompt
            strategy = PromptStrategy.STRUCTURED
        elif retry_count == 1:
            # Second attempt: use error prevention
            strategy = PromptStrategy.ERROR_PREVENTION
        else:
            # Third attempt: use adaptive prompt
            return self.prompt_engineer.create_adaptive_prompt(input_text, previous_issues)
        
        return self.prompt_engineer.create_enhanced_prompt(input_text, strategy)
    
    def _translate_with_real_time_validation(self, input_text: str, prompt: str) -> Tuple[str, Dict]:
        """Translate với real-time validation"""
        # For now, simulate stream validation
        # In real implementation, this would use actual streaming
        output_text = self.translator_service.translate_text(prompt)
        
        # Simulate stream validation
        stream_validation = {
            'needs_correction': False,
            'blocks_found': len(self.block_manager.extract_blocks_with_info(output_text)),
            'expected_blocks': len(self.block_manager.extract_blocks_with_info(input_text))
        }
        
        return output_text, stream_validation
    
    def _should_apply_context_awareness(self, input_analysis: Dict) -> bool:
        """Check if should apply context awareness"""
        # Apply context awareness if:
        # 1. Many blocks (> 10)
        # 2. No duplicate issues
        # 3. Complex content
        return (input_analysis['total_blocks'] > 10 and 
                not input_analysis['has_issues'])
    
    def _final_validation(self, input_text: str, output_text: str) -> Dict:
        """Final validation trước khi return success"""
        input_blocks = self.block_manager.extract_blocks_with_info(input_text)
        output_blocks = self.block_manager.extract_blocks_with_info(output_text)
        
        validation = self.block_manager.validate_block_consistency(input_blocks, output_blocks)
        
        return {
            'is_valid': validation['is_valid'],
            'errors': validation.get('errors', []),
            'warnings': validation.get('warnings', []),
            'block_count_match': len(input_blocks) == len(output_blocks),
            'missing_blocks': validation.get('missing_blocks', [])
        }
    
    def _write_output(self, content: str, output_path: str):
        """Write output với normalization"""
        normalized = "\n".join(l.strip() for l in content.splitlines() if l.strip())
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(normalized + ("\n" if not normalized.endswith("\n") else ""))
    
    def get_processing_summary(self, result: ProcessingResult) -> str:
        """Get processing summary"""
        summary = f"""
🎯 MASTER PROCESSING SUMMARY
============================
✅ Success: {result.success}
⏱️ Processing Time: {result.processing_time:.2f}s
🔄 Retry Count: {result.retry_count}
📊 Quality Score: {result.quality_score:.2f}
🎯 Confidence Level: {result.confidence_level}

📋 Issues Detected: {len(result.issues_detected)}
"""
        
        if result.issues_detected:
            summary += "\n🚨 Issues:\n"
            for issue in result.issues_detected:
                summary += f"  - {issue}\n"
        
        if result.recommendations:
            summary += "\n💡 Recommendations:\n"
            for rec in result.recommendations:
                summary += f"  - {rec}\n"
        
        return summary
    
    def set_processing_mode(self, *_args, **_kwargs):
        """
        Backwards-compatible shim: processing mode is fixed to the enhanced pipeline.
        Calling this method will not change runtime behavior; it logs a clear message
        explaining that the mode is now fixed and how to change tuning parameters.
        """
        self._log('info', (
            "set_processing_mode() called but the runtime now uses a single "
            "enhanced pipeline. To adjust behavior, edit your config (e.g. 'enhanced_features' "
            "section) or create a custom ProcessingConfig and pass it to process_file()."
        ))
    
    def get_component_status(self) -> Dict:
        """Get status của tất cả components"""
        return {
            'block_manager': '✅ Ready',
            'prompt_engineer': '✅ Ready',
            'error_classifier': '✅ Ready',
            'stream_validator': '✅ Ready',
            'context_translator': '✅ Ready',
            'quality_assurance': '✅ Ready',
            'processing_mode': self.config.mode,
            'max_retries': self.config.max_retries,
            'confidence_threshold': self.config.confidence_threshold
        }
