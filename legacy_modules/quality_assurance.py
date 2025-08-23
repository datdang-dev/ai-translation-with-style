"""
@brief QualityAssurance: Multi-model validation và confidence scoring
"""
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import re
import time

class ValidationLevel(Enum):
    STRUCTURE = "structure"
    CONTENT = "content"
    CONSISTENCY = "consistency"
    QUALITY = "quality"

@dataclass
class ValidationResult:
    """Kết quả validation"""
    level: ValidationLevel
    passed: bool
    score: float  # 0.0 to 1.0
    issues: List[str] = None
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.suggestions is None:
            self.suggestions = []

@dataclass
class QualityReport:
    """Quality report tổng hợp"""
    overall_score: float
    confidence_level: str  # 'high', 'medium', 'low'
    validation_results: Dict[str, ValidationResult]
    critical_issues: List[str]
    recommendations: List[str]
    processing_time: float

class QualityAssurance:
    """
    Quality Assurance Pipeline với multi-model validation
    """
    
    def __init__(self, block_manager, logger=None):
        self.block_manager = block_manager
        self.logger = logger
        
        # Initialize validators
        self.validators = {
            'structure_validator': self._structure_validator,
            'content_validator': self._content_validator,
            'consistency_validator': self._consistency_validator,
            'quality_validator': self._quality_validator
        }
        
        # Quality thresholds
        self.thresholds = {
            'high_confidence': 0.8,
            'medium_confidence': 0.6,
            'low_confidence': 0.4
        }
    
    def set_logger(self, logger):
        self.logger = logger
    
    def _log(self, level: str, msg: str):
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(f"[{level.upper()}] {msg}")
    
    def validate_translation(self, input_text: str, output_text: str) -> QualityReport:
        """
        Validate translation với multi-model approach
        """
        start_time = time.time()
        
        self._log('info', f"🔍 Starting quality assurance validation...")
        
        # Run all validators
        validation_results = {}
        for validator_name, validator_func in self.validators.items():
            try:
                result = validator_func(input_text, output_text)
                validation_results[validator_name] = result
                
                self._log('info', f"📊 {validator_name}: {'✅ PASS' if result.passed else '❌ FAIL'} (score: {result.score:.2f})")
                
            except Exception as e:
                self._log('error', f"❌ {validator_name} failed: {e}")
                validation_results[validator_name] = ValidationResult(
                    level=ValidationLevel.STRUCTURE,
                    passed=False,
                    score=0.0,
                    issues=[f"Validator error: {e}"],
                    suggestions=["Check validator implementation"]
                )
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(validation_results)
        
        # Determine confidence level
        confidence_level = self._determine_confidence_level(overall_score)
        
        # Collect critical issues
        critical_issues = self._collect_critical_issues(validation_results)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(validation_results, overall_score)
        
        processing_time = time.time() - start_time
        
        report = QualityReport(
            overall_score=overall_score,
            confidence_level=confidence_level,
            validation_results=validation_results,
            critical_issues=critical_issues,
            recommendations=recommendations,
            processing_time=processing_time
        )
        
        self._log('info', f"✅ Quality assurance completed in {processing_time:.2f}s")
        self._log('info', f"📊 Overall score: {overall_score:.2f} ({confidence_level} confidence)")
        
        return report
    
    def _structure_validator(self, input_text: str, output_text: str) -> ValidationResult:
        """Validate structure consistency"""
        input_blocks = self.block_manager.extract_blocks_with_info(input_text)
        output_blocks = self.block_manager.extract_blocks_with_info(output_text)
        
        validation = self.block_manager.validate_block_consistency(input_blocks, output_blocks)
        
        issues = []
        score = 1.0
        
        # Check block count
        if len(input_blocks) != len(output_blocks):
            issues.append(f"Block count mismatch: input={len(input_blocks)}, output={len(output_blocks)}")
            score -= 0.3
        
        # Check missing blocks
        if validation['missing_blocks']:
            issues.append(f"Missing blocks: {validation['missing_blocks']}")
            score -= 0.4
        
        # Check duplicate IDs
        if validation['duplicate_input_ids'] or validation['duplicate_output_ids']:
            issues.append(f"Duplicate IDs detected")
            score -= 0.2
        
        # Check mismatched IDs
        if validation['mismatched_ids']:
            issues.append(f"Mismatched IDs: {validation['mismatched_ids']}")
            score -= 0.3
        
        score = max(0.0, score)
        
        suggestions = []
        if issues:
            suggestions.extend([
                "Ensure all input blocks are translated",
                "Check for duplicate block IDs",
                "Verify block ID consistency"
            ])
        
        return ValidationResult(
            level=ValidationLevel.STRUCTURE,
            passed=len(issues) == 0,
            score=score,
            issues=issues,
            suggestions=suggestions
        )
    
    def _content_validator(self, input_text: str, output_text: str) -> ValidationResult:
        """Validate content quality"""
        input_blocks = self.block_manager.extract_blocks_with_info(input_text)
        output_blocks = self.block_manager.extract_blocks_with_info(output_text)
        
        issues = []
        score = 1.0
        
        # Check for empty blocks
        empty_blocks = 0
        for block in output_blocks:
            if not block.content.strip() or block.content.strip() == block.id:
                empty_blocks += 1
        
        if empty_blocks > 0:
            issues.append(f"Empty blocks: {empty_blocks}")
            score -= 0.2 * (empty_blocks / len(output_blocks))
        
        # Check for placeholder content
        placeholder_count = 0
        for block in output_blocks:
            if any(placeholder in block.content.lower() for placeholder in ['[needs_review]', '[empty]', '[placeholder]']):
                placeholder_count += 1
        
        if placeholder_count > 0:
            issues.append(f"Placeholder content: {placeholder_count} blocks")
            score -= 0.3 * (placeholder_count / len(output_blocks))
        
        # Check for translation quality indicators
        quality_indicators = self._check_translation_quality(output_blocks)
        if quality_indicators['issues']:
            issues.extend(quality_indicators['issues'])
            score -= quality_indicators['score_deduction']
        
        score = max(0.0, score)
        
        suggestions = []
        if issues:
            suggestions.extend([
                "Review empty or placeholder blocks",
                "Check translation quality",
                "Ensure all content is properly translated"
            ])
        
        return ValidationResult(
            level=ValidationLevel.CONTENT,
            passed=len(issues) == 0,
            score=score,
            issues=issues,
            suggestions=suggestions
        )
    
    def _consistency_validator(self, input_text: str, output_text: str) -> ValidationResult:
        """Validate consistency across blocks"""
        input_blocks = self.block_manager.extract_blocks_with_info(input_text)
        output_blocks = self.block_manager.extract_blocks_with_info(output_text)
        
        issues = []
        score = 1.0
        
        # Check character name consistency
        character_consistency = self._check_character_consistency(input_blocks, output_blocks)
        if character_consistency['issues']:
            issues.extend(character_consistency['issues'])
            score -= character_consistency['score_deduction']
        
        # Check style consistency
        style_consistency = self._check_style_consistency(output_blocks)
        if style_consistency['issues']:
            issues.extend(style_consistency['issues'])
            score -= style_consistency['score_deduction']
        
        # Check terminology consistency
        terminology_consistency = self._check_terminology_consistency(output_blocks)
        if terminology_consistency['issues']:
            issues.extend(terminology_consistency['issues'])
            score -= terminology_consistency['score_deduction']
        
        score = max(0.0, score)
        
        suggestions = []
        if issues:
            suggestions.extend([
                "Maintain consistent character names",
                "Use consistent translation style",
                "Ensure terminology consistency"
            ])
        
        return ValidationResult(
            level=ValidationLevel.CONSISTENCY,
            passed=len(issues) == 0,
            score=score,
            issues=issues,
            suggestions=suggestions
        )
    
    def _quality_validator(self, input_text: str, output_text: str) -> ValidationResult:
        """Validate overall translation quality"""
        output_blocks = self.block_manager.extract_blocks_with_info(output_text)
        
        issues = []
        score = 1.0
        
        # Check for common translation errors
        error_patterns = [
            r'\b[A-Z]{2,}\b',  # ALL CAPS words
            r'[.!?]{2,}',      # Multiple punctuation
            r'\s{2,}',         # Multiple spaces
            r'[^\w\s\.,!?;:()\[\]{}"\'-]',  # Unusual characters
        ]
        
        error_count = 0
        for block in output_blocks:
            for pattern in error_patterns:
                if re.search(pattern, block.content):
                    error_count += 1
                    break
        
        if error_count > 0:
            issues.append(f"Formatting issues: {error_count} blocks")
            score -= 0.2 * (error_count / len(output_blocks))
        
        # Check for readability
        readability_score = self._calculate_readability(output_blocks)
        if readability_score < 0.7:
            issues.append(f"Low readability score: {readability_score:.2f}")
            score -= 0.3
        
        # Check for natural language flow
        flow_score = self._check_natural_flow(output_blocks)
        if flow_score < 0.6:
            issues.append(f"Poor natural flow: {flow_score:.2f}")
            score -= 0.2
        
        score = max(0.0, score)
        
        suggestions = []
        if issues:
            suggestions.extend([
                "Fix formatting issues",
                "Improve readability",
                "Enhance natural language flow"
            ])
        
        return ValidationResult(
            level=ValidationLevel.QUALITY,
            passed=len(issues) == 0,
            score=score,
            issues=issues,
            suggestions=suggestions
        )
    
    def _check_translation_quality(self, output_blocks: List) -> Dict:
        """Check translation quality indicators"""
        issues = []
        score_deduction = 0.0
        
        # Check for untranslated English words
        english_word_count = 0
        for block in output_blocks:
            english_words = re.findall(r'\b[a-zA-Z]{3,}\b', block.content)
            english_word_count += len(english_words)
        
        if english_word_count > len(output_blocks) * 2:
            issues.append(f"Too many English words: {english_word_count}")
            score_deduction += 0.2
        
        # Check for literal translations
        literal_indicators = ['literal', 'word-for-word', 'direct translation']
        literal_count = 0
        for block in output_blocks:
            if any(indicator in block.content.lower() for indicator in literal_indicators):
                literal_count += 1
        
        if literal_count > 0:
            issues.append(f"Literal translation indicators: {literal_count}")
            score_deduction += 0.1
        
        return {
            'issues': issues,
            'score_deduction': score_deduction
        }
    
    def _check_character_consistency(self, input_blocks: List, output_blocks: List) -> Dict:
        """Check character name consistency"""
        issues = []
        score_deduction = 0.0
        
        # Extract character names from input and output
        input_names = self._extract_character_names(input_blocks)
        output_names = self._extract_character_names(output_blocks)
        
        # Check for missing or inconsistent names
        missing_names = input_names - output_names
        if missing_names:
            issues.append(f"Missing character names: {missing_names}")
            score_deduction += 0.2
        
        # Check for inconsistent name variations
        name_variations = self._find_name_variations(output_names)
        if name_variations:
            issues.append(f"Inconsistent name variations: {name_variations}")
            score_deduction += 0.1
        
        return {
            'issues': issues,
            'score_deduction': score_deduction
        }
    
    def _extract_character_names(self, blocks: List) -> set:
        """Extract character names từ blocks"""
        names = set()
        
        # Simple pattern matching for character names
        name_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
            r'\b[A-Z][a-z]+-[A-Z][a-z]+\b',  # First-Last
            r'\b[A-Z][a-z]+-chan\b',         # Japanese honorifics
            r'\b[A-Z][a-z]+-san\b',
            r'\b[A-Z][a-z]+-kun\b',
        ]
        
        for block in blocks:
            for pattern in name_patterns:
                matches = re.findall(pattern, block.content)
                names.update(matches)
        
        return names
    
    def _find_name_variations(self, names: set) -> List[str]:
        """Find inconsistent name variations"""
        variations = []
        name_parts = {}
        
        for name in names:
            parts = name.split()
            if len(parts) >= 2:
                first = parts[0]
                if first in name_parts and name_parts[first] != name:
                    variations.append(f"{first}: {name_parts[first]} vs {name}")
                else:
                    name_parts[first] = name
        
        return variations
    
    def _check_style_consistency(self, output_blocks: List) -> Dict:
        """Check translation style consistency"""
        issues = []
        score_deduction = 0.0
        
        # Check for style variations
        styles = []
        for block in output_blocks:
            style = self._detect_translation_style(block.content)
            styles.append(style)
        
        # Count style variations
        style_counts = {}
        for style in styles:
            style_counts[style] = style_counts.get(style, 0) + 1
        
        if len(style_counts) > 3:  # Too many style variations
            issues.append(f"Too many style variations: {list(style_counts.keys())}")
            score_deduction += 0.1
        
        return {
            'issues': issues,
            'score_deduction': score_deduction
        }
    
    def _detect_translation_style(self, content: str) -> str:
        """Detect translation style"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['formal', 'polite', 'respectful']):
            return 'formal'
        elif any(word in content_lower for word in ['casual', 'informal', 'friendly']):
            return 'casual'
        elif any(word in content_lower for word in ['vulgar', 'rude', 'crude']):
            return 'vulgar'
        else:
            return 'neutral'
    
    def _check_terminology_consistency(self, output_blocks: List) -> Dict:
        """Check terminology consistency"""
        issues = []
        score_deduction = 0.0
        
        # Extract technical terms
        technical_terms = self._extract_technical_terms(output_blocks)
        
        # Check for inconsistent translations
        term_variations = self._find_term_variations(technical_terms)
        if term_variations:
            issues.append(f"Inconsistent terminology: {term_variations}")
            score_deduction += 0.1
        
        return {
            'issues': issues,
            'score_deduction': score_deduction
        }
    
    def _extract_technical_terms(self, blocks: List) -> Dict[str, List[str]]:
        """Extract technical terms và their translations"""
        terms = {}
        
        # Simple pattern for technical terms
        for block in blocks:
            # Look for terms in quotes or brackets
            quoted_terms = re.findall(r'["\']([^"\']+)["\']', block.content)
            bracketed_terms = re.findall(r'\[([^\]]+)\]', block.content)
            
            for term in quoted_terms + bracketed_terms:
                if len(term) > 3:  # Filter out short terms
                    if term not in terms:
                        terms[term] = []
                    terms[term].append(block.content)
        
        return terms
    
    def _find_term_variations(self, terms: Dict[str, List[str]]) -> List[str]:
        """Find inconsistent term translations"""
        variations = []
        
        for term, contexts in terms.items():
            if len(contexts) > 1:
                # Check if term is translated consistently
                translations = set()
                for context in contexts:
                    # Extract translation from context
                    # This is a simplified version
                    pass
        
        return variations
    
    def _calculate_readability(self, output_blocks: List) -> float:
        """Calculate readability score"""
        if not output_blocks:
            return 0.0
        
        total_sentences = 0
        total_words = 0
        total_syllables = 0
        
        for block in output_blocks:
            sentences = re.split(r'[.!?]+', block.content)
            total_sentences += len(sentences)
            
            words = re.findall(r'\b\w+\b', block.content)
            total_words += len(words)
            
            # Simplified syllable count
            syllables = sum(len(re.findall(r'[aeiouy]', word.lower())) for word in words)
            total_syllables += syllables
        
        if total_sentences == 0 or total_words == 0:
            return 0.0
        
        # Flesch Reading Ease (simplified)
        avg_sentence_length = total_words / total_sentences
        avg_syllables_per_word = total_syllables / total_words
        
        readability = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        
        return max(0.0, min(1.0, readability / 100.0))
    
    def _check_natural_flow(self, output_blocks: List) -> float:
        """Check natural language flow"""
        if not output_blocks:
            return 0.0
        
        flow_score = 0.0
        total_blocks = len(output_blocks)
        
        for i in range(1, len(output_blocks)):
            prev_block = output_blocks[i-1]
            curr_block = output_blocks[i]
            
            # Check for natural transitions
            transition_score = self._check_transition(prev_block.content, curr_block.content)
            flow_score += transition_score
        
        return flow_score / (total_blocks - 1) if total_blocks > 1 else 1.0
    
    def _check_transition(self, prev_content: str, curr_content: str) -> float:
        """Check transition between two blocks"""
        # Simple transition check
        prev_words = set(re.findall(r'\b\w+\b', prev_content.lower()))
        curr_words = set(re.findall(r'\b\w+\b', curr_content.lower()))
        
        # Check for common words
        common_words = prev_words.intersection(curr_words)
        
        if len(common_words) > 0:
            return 0.8  # Good transition
        else:
            return 0.4  # Poor transition
    
    def _calculate_overall_score(self, validation_results: Dict[str, ValidationResult]) -> float:
        """Calculate overall quality score"""
        if not validation_results:
            return 0.0
        
        # Weighted average based on validation level importance
        weights = {
            'structure_validator': 0.4,    # Most important
            'content_validator': 0.3,      # Important
            'consistency_validator': 0.2,  # Medium importance
            'quality_validator': 0.1       # Least important
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for validator_name, result in validation_results.items():
            weight = weights.get(validator_name, 0.1)
            weighted_sum += result.score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _determine_confidence_level(self, score: float) -> str:
        """Determine confidence level từ score"""
        if score >= self.thresholds['high_confidence']:
            return 'high'
        elif score >= self.thresholds['medium_confidence']:
            return 'medium'
        elif score >= self.thresholds['low_confidence']:
            return 'low'
        else:
            return 'very_low'
    
    def _collect_critical_issues(self, validation_results: Dict[str, ValidationResult]) -> List[str]:
        """Collect critical issues từ all validators"""
        critical_issues = []
        
        for validator_name, result in validation_results.items():
            if not result.passed and result.score < 0.5:
                critical_issues.extend(result.issues)
        
        return list(set(critical_issues))  # Remove duplicates
    
    def _generate_recommendations(self, validation_results: Dict[str, ValidationResult], overall_score: float) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Overall score recommendations
        if overall_score < 0.5:
            recommendations.append("Consider complete retranslation")
        elif overall_score < 0.7:
            recommendations.append("Review and fix identified issues")
        elif overall_score < 0.9:
            recommendations.append("Minor improvements recommended")
        else:
            recommendations.append("Translation quality is good")
        
        # Specific recommendations from validators
        for validator_name, result in validation_results.items():
            if not result.passed:
                recommendations.extend(result.suggestions)
        
        return list(set(recommendations))  # Remove duplicates
    
    def get_confidence_score(self, input_text: str, output_text: str) -> float:
        """Calculate confidence score cho translation quality"""
        report = self.validate_translation(input_text, output_text)
        return report.overall_score
