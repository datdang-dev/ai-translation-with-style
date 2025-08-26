"""
Validator service for translation quality and content validation
"""

import re
import difflib
from typing import List, Dict, Any, Optional, Callable
from abc import ABC, abstractmethod
from services.models import ValidationError
from services.common.logger import get_logger


class IValidator(ABC):
    """Interface for validation rules"""
    
    @abstractmethod
    def validate(self, original: str, translated: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate translation"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get validator name"""
        pass


class LengthValidator(IValidator):
    """Validates translation length relative to original"""
    
    def __init__(self, 
                 min_ratio: float = 0.3,
                 max_ratio: float = 3.0,
                 allow_empty: bool = False):
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
        self.allow_empty = allow_empty
    
    def get_name(self) -> str:
        return "length_validator"
    
    def validate(self, original: str, translated: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate translation length"""
        original_len = len(original.strip())
        translated_len = len(translated.strip())
        
        # Handle empty translations
        if translated_len == 0:
            if self.allow_empty or original_len == 0:
                return {'valid': True, 'score': 1.0, 'message': 'Empty translation accepted'}
            else:
                return {'valid': False, 'score': 0.0, 'message': 'Translation is empty'}
        
        # Handle empty original
        if original_len == 0:
            return {'valid': True, 'score': 1.0, 'message': 'Original is empty'}
        
        # Calculate length ratio
        ratio = translated_len / original_len
        
        if ratio < self.min_ratio:
            return {
                'valid': False,
                'score': ratio / self.min_ratio,
                'message': f'Translation too short (ratio: {ratio:.2f}, min: {self.min_ratio})'
            }
        elif ratio > self.max_ratio:
            return {
                'valid': False,
                'score': self.max_ratio / ratio,
                'message': f'Translation too long (ratio: {ratio:.2f}, max: {self.max_ratio})'
            }
        else:
            # Calculate score based on how close to ideal ratio (1.0)
            ideal_distance = abs(ratio - 1.0)
            max_distance = max(1.0 - self.min_ratio, self.max_ratio - 1.0)
            score = 1.0 - (ideal_distance / max_distance)
            
            return {
                'valid': True,
                'score': score,
                'message': f'Length ratio acceptable: {ratio:.2f}'
            }


class SpecialCharactersValidator(IValidator):
    """Validates preservation of special characters and formatting"""
    
    def __init__(self, preserve_patterns: List[str] = None):
        self.preserve_patterns = preserve_patterns or [
            r'\{[^}]*\}',      # {variables}
            r'\[[^\]]*\]',     # [tags]
            r'<[^>]*>',        # <html tags>
            r'%[sd%]',         # %s, %d, %%
            r'\$\w+',          # $variables
            r'#\w+',           # #hashtags
            r'@\w+',           # @mentions
        ]
        
        self.compiled_patterns = [re.compile(pattern) for pattern in self.preserve_patterns]
    
    def get_name(self) -> str:
        return "special_characters_validator"
    
    def validate(self, original: str, translated: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate special character preservation"""
        original_specials = self._extract_special_chars(original)
        translated_specials = self._extract_special_chars(translated)
        
        missing_specials = original_specials - translated_specials
        extra_specials = translated_specials - original_specials
        
        if not missing_specials and not extra_specials:
            return {
                'valid': True,
                'score': 1.0,
                'message': 'All special characters preserved'
            }
        
        total_specials = len(original_specials)
        if total_specials == 0:
            # No special characters to preserve
            if extra_specials:
                return {
                    'valid': False,
                    'score': 0.5,
                    'message': f'Unexpected special characters added: {list(extra_specials)}'
                }
            return {'valid': True, 'score': 1.0, 'message': 'No special characters to validate'}
        
        preserved_count = len(original_specials - missing_specials)
        score = preserved_count / total_specials
        
        issues = []
        if missing_specials:
            issues.append(f'Missing: {list(missing_specials)}')
        if extra_specials:
            issues.append(f'Extra: {list(extra_specials)}')
        
        return {
            'valid': score >= 0.8,  # Allow some tolerance
            'score': score,
            'message': f'Special characters: {score:.1%} preserved. {"; ".join(issues)}'
        }
    
    def _extract_special_chars(self, text: str) -> set:
        """Extract special characters and patterns from text"""
        specials = set()
        
        for pattern in self.compiled_patterns:
            matches = pattern.findall(text)
            specials.update(matches)
        
        return specials


class ContentConsistencyValidator(IValidator):
    """Validates content consistency and meaning preservation"""
    
    def __init__(self):
        self.suspicious_patterns = [
            r'^[A-Z\s]+$',      # ALL CAPS (might be untranslated)
            r'^[a-z\s]+$',      # all lowercase (might be untranslated)
            r'^\w+$',           # Single word (might be untranslated)
            r'^[^\w\s]+$',      # Only special characters
        ]
        
        self.compiled_suspicious = [re.compile(pattern) for pattern in self.suspicious_patterns]
    
    def get_name(self) -> str:
        return "content_consistency_validator"
    
    def validate(self, original: str, translated: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate content consistency"""
        original_clean = original.strip()
        translated_clean = translated.strip()
        
        # Check if translation is identical to original (might be untranslated)
        if original_clean.lower() == translated_clean.lower():
            # Check if it's a proper noun or special term that shouldn't be translated
            if self._looks_like_proper_noun(original_clean):
                return {
                    'valid': True,
                    'score': 1.0,
                    'message': 'Proper noun or special term preserved'
                }
            else:
                return {
                    'valid': False,
                    'score': 0.3,
                    'message': 'Translation identical to original (possibly untranslated)'
                }
        
        # Check for suspicious patterns
        suspicion_score = self._check_suspicious_patterns(translated_clean)
        
        # Check similarity (too similar might indicate poor translation)
        similarity = self._calculate_similarity(original_clean, translated_clean)
        
        # Calculate overall score
        if suspicion_score < 0.5:
            return {
                'valid': False,
                'score': suspicion_score,
                'message': 'Translation appears suspicious or low quality'
            }
        
        if similarity > 0.9:
            return {
                'valid': False,
                'score': 0.4,
                'message': f'Translation too similar to original (similarity: {similarity:.2f})'
            }
        
        # Good translation
        final_score = min(suspicion_score, 1.0 - similarity * 0.5)
        return {
            'valid': True,
            'score': final_score,
            'message': f'Content appears consistent (similarity: {similarity:.2f})'
        }
    
    def _looks_like_proper_noun(self, text: str) -> bool:
        """Check if text looks like a proper noun or special term"""
        # Heuristics for proper nouns
        words = text.split()
        
        # Single capitalized word
        if len(words) == 1 and words[0][0].isupper():
            return True
        
        # All words capitalized
        if all(word[0].isupper() for word in words if word):
            return True
        
        # Common proper noun patterns
        if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$', text):
            return True
        
        return False
    
    def _check_suspicious_patterns(self, text: str) -> float:
        """Check for suspicious translation patterns"""
        for pattern in self.compiled_suspicious:
            if pattern.match(text):
                return 0.3  # Low score for suspicious patterns
        
        return 1.0  # No suspicious patterns found
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity"""
        return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


class ValidatorService:
    """Main validation service that coordinates multiple validators"""
    
    def __init__(self):
        self.validators: Dict[str, IValidator] = {}
        self.logger = get_logger("ValidatorService")
        
        # Register default validators
        self._register_default_validators()
    
    def _register_default_validators(self):
        """Register built-in validators"""
        self.register_validator(LengthValidator())
        self.register_validator(SpecialCharactersValidator())
        self.register_validator(ContentConsistencyValidator())
    
    def register_validator(self, validator: IValidator):
        """Register a new validator"""
        name = validator.get_name()
        self.validators[name] = validator
        self.logger.info(f"Registered validator: {name}")
    
    def unregister_validator(self, name: str):
        """Unregister a validator"""
        if name in self.validators:
            del self.validators[name]
            self.logger.info(f"Unregistered validator: {name}")
    
    def validate_translation(self, 
                           original: str, 
                           translated: str,
                           context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate a single translation using all validators"""
        if not self.validators:
            return {
                'valid': True,
                'overall_score': 1.0,
                'message': 'No validators configured',
                'validator_results': {}
            }
        
        validator_results = {}
        scores = []
        all_valid = True
        messages = []
        
        # Run all validators
        for name, validator in self.validators.items():
            try:
                result = validator.validate(original, translated, context)
                validator_results[name] = result
                
                if 'score' in result:
                    scores.append(result['score'])
                
                if not result.get('valid', False):
                    all_valid = False
                
                if 'message' in result:
                    messages.append(f"{name}: {result['message']}")
                    
            except Exception as e:
                self.logger.error(f"Validator {name} failed: {e}")
                validator_results[name] = {
                    'valid': False,
                    'score': 0.0,
                    'message': f"Validator error: {e}"
                }
                all_valid = False
                scores.append(0.0)
        
        # Calculate overall score
        overall_score = sum(scores) / len(scores) if scores else 0.0
        
        return {
            'valid': all_valid and overall_score >= 0.6,  # Threshold for overall validity
            'overall_score': overall_score,
            'message': '; '.join(messages),
            'validator_results': validator_results
        }
    
    def validate_batch(self, 
                      originals: List[str], 
                      translations: List[str],
                      context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Validate batch of translations"""
        if len(originals) != len(translations):
            raise ValidationError("Originals and translations must have same length")
        
        results = []
        for original, translated in zip(originals, translations):
            result = self.validate_translation(original, translated, context)
            results.append(result)
        
        return results
    
    def get_validation_summary(self, validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary statistics for validation results"""
        if not validation_results:
            return {
                'total_translations': 0,
                'valid_translations': 0,
                'invalid_translations': 0,
                'validity_rate': 0.0,
                'average_score': 0.0
            }
        
        total = len(validation_results)
        valid_count = sum(1 for result in validation_results if result.get('valid', False))
        scores = [result.get('overall_score', 0.0) for result in validation_results]
        
        return {
            'total_translations': total,
            'valid_translations': valid_count,
            'invalid_translations': total - valid_count,
            'validity_rate': valid_count / total,
            'average_score': sum(scores) / len(scores),
            'min_score': min(scores),
            'max_score': max(scores)
        }
    
    def validate_length(self, original: str, translated: str) -> bool:
        """Quick length validation"""
        length_validator = self.validators.get('length_validator')
        if length_validator:
            result = length_validator.validate(original, translated)
            return result.get('valid', False)
        return True
    
    def validate_special_chars(self, original: str, translated: str) -> bool:
        """Quick special characters validation"""
        special_validator = self.validators.get('special_characters_validator')
        if special_validator:
            result = special_validator.validate(original, translated)
            return result.get('valid', False)
        return True
    
    def get_validators(self) -> List[str]:
        """Get list of registered validator names"""
        return list(self.validators.keys())
    
    def get_validator_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all validators"""
        info = {}
        for name, validator in self.validators.items():
            info[name] = {
                'name': name,
                'class': type(validator).__name__,
                'description': validator.__doc__ or 'No description available'
            }
        return info
    
    def set_validation_thresholds(self, 
                                length_min_ratio: float = None,
                                length_max_ratio: float = None):
        """Update validation thresholds"""
        length_validator = self.validators.get('length_validator')
        if length_validator and isinstance(length_validator, LengthValidator):
            if length_min_ratio is not None:
                length_validator.min_ratio = length_min_ratio
            if length_max_ratio is not None:
                length_validator.max_ratio = length_max_ratio
            
            self.logger.info(f"Updated length validation thresholds: min={length_validator.min_ratio}, max={length_validator.max_ratio}")
    
    def create_custom_validator(self, 
                              name: str, 
                              validation_func: Callable[[str, str, Dict], Dict[str, Any]]) -> IValidator:
        """Create a custom validator from a function"""
        
        class CustomValidator(IValidator):
            def __init__(self, name: str, func: Callable):
                self.name = name
                self.func = func
            
            def get_name(self) -> str:
                return self.name
            
            def validate(self, original: str, translated: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
                return self.func(original, translated, context or {})
        
        custom_validator = CustomValidator(name, validation_func)
        self.register_validator(custom_validator)
        return custom_validator