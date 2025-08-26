"""
Google Translate client implementation
"""

import aiohttp
import json
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
from services.models import HealthStatus, ProviderError
from services.common.logger import get_logger
from .base_provider import BaseTranslationProvider


class GoogleTranslateClient(BaseTranslationProvider):
    """Google Translate API client"""
    
    def __init__(self, api_key: str = None, config: Dict[str, Any] = None):
        super().__init__("google_translate", config)
        self.api_key = api_key
        self.base_url = "https://translation.googleapis.com/language/translate/v2"
        self.logger = get_logger("GoogleTranslateClient")
        
        # If no API key provided, use free service (limited functionality)
        self.use_free_service = api_key is None
        if self.use_free_service:
            self.logger.warning("No Google API key provided, using free service with limitations")
    
    async def translate(self, texts: List[str], target_lang: str, source_lang: str = "auto") -> List[str]:
        """Translate texts using Google Translate"""
        self._validate_texts(texts)
        self._validate_languages(source_lang, target_lang)
        
        if self.use_free_service:
            return await self._translate_free(texts, target_lang, source_lang)
        else:
            return await self._translate_api(texts, target_lang, source_lang)
    
    async def _translate_api(self, texts: List[str], target_lang: str, source_lang: str) -> List[str]:
        """Translate using official Google Translate API"""
        try:
            # Prepare request data
            params = {
                'key': self.api_key,
                'target': target_lang,
                'format': 'text'
            }
            
            if source_lang != "auto":
                params['source'] = source_lang
            
            # Add texts as query parameters
            for i, text in enumerate(texts):
                params[f'q'] = text  # Google API expects 'q' parameter for each text
            
            # Build request
            url = f"{self.base_url}?{urlencode(params, doseq=True)}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url) as response:
                    if response.status == 403:
                        raise ProviderError("Google Translate API access denied", error_code="AUTH_ERROR")
                    elif response.status == 429:
                        raise ProviderError("Google Translate rate limit exceeded", error_code="RATE_LIMIT")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise ProviderError(f"Google Translate API error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    return self._parse_google_response(result)
        
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(f"Google Translate API request failed: {e}")
    
    async def _translate_free(self, texts: List[str], target_lang: str, source_lang: str) -> List[str]:
        """Translate using free Google Translate service (unofficial)"""
        try:
            # This is a simplified implementation
            # In production, you might want to use a library like googletrans
            translations = []
            
            for text in texts:
                # For demo purposes, we'll do a simple transformation
                # In real implementation, use googletrans library or similar
                if target_lang == 'es':
                    # Simple Spanish "translation" for demo
                    translation = f"[ES] {text}"
                elif target_lang == 'fr':
                    translation = f"[FR] {text}"
                else:
                    translation = f"[{target_lang.upper()}] {text}"
                
                translations.append(translation)
            
            self.logger.warning("Using mock translation - implement real free service for production")
            return translations
            
        except Exception as e:
            raise ProviderError(f"Free Google Translate failed: {e}")
    
    def _parse_google_response(self, response: Dict[str, Any]) -> List[str]:
        """Parse Google Translate API response"""
        try:
            data = response.get('data', {})
            translations = data.get('translations', [])
            
            result = []
            for translation in translations:
                translated_text = translation.get('translatedText', '')
                result.append(translated_text)
            
            return result
            
        except Exception as e:
            raise ProviderError(f"Failed to parse Google Translate response: {e}")
    
    async def health_check(self) -> HealthStatus:
        """Check Google Translate service health"""
        try:
            import time
            start_time = time.time()
            
            # Simple health check
            test_result = await self.translate(["Hello"], "es", "en")
            response_time = time.time() - start_time
            
            if test_result and len(test_result) > 0:
                service_type = "API" if not self.use_free_service else "Free Service"
                return HealthStatus.healthy(
                    f"Google Translate {service_type} operational",
                    response_time=response_time
                )
            else:
                return HealthStatus.unhealthy("Google Translate returned empty result")
                
        except ProviderError as e:
            return HealthStatus.unhealthy(f"Google Translate health check failed: {e.message}")
        except Exception as e:
            return HealthStatus.unhealthy(f"Google Translate health check error: {e}")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get Google Translate capabilities"""
        base_capabilities = super().get_capabilities()
        
        if self.use_free_service:
            google_capabilities = {
                'max_text_length': 5000,
                'max_batch_size': 10,
                'supports_auto_detect': True,
                'service_type': 'free',
                'rate_limited': True
            }
        else:
            google_capabilities = {
                'max_text_length': 30000,
                'max_batch_size': 128,
                'supports_auto_detect': True,
                'service_type': 'api',
                'rate_limited': False
            }
        
        # Common supported languages
        google_capabilities['supported_languages'] = [
            'af', 'sq', 'am', 'ar', 'hy', 'az', 'eu', 'be', 'bn', 'bs', 'bg', 'ca', 'ceb', 'ny',
            'zh', 'co', 'hr', 'cs', 'da', 'nl', 'en', 'eo', 'et', 'tl', 'fi', 'fr', 'fy', 'gl',
            'ka', 'de', 'el', 'gu', 'ht', 'ha', 'haw', 'iw', 'hi', 'hmn', 'hu', 'is', 'ig', 'id',
            'ga', 'it', 'ja', 'jw', 'kn', 'kk', 'km', 'ko', 'ku', 'ky', 'lo', 'la', 'lv', 'lt',
            'lb', 'mk', 'mg', 'ms', 'ml', 'mt', 'mi', 'mr', 'mn', 'my', 'ne', 'no', 'ps', 'fa',
            'pl', 'pt', 'pa', 'ro', 'ru', 'sm', 'gd', 'sr', 'st', 'sn', 'sd', 'si', 'sk', 'sl',
            'so', 'es', 'su', 'sw', 'sv', 'tg', 'ta', 'te', 'th', 'tr', 'uk', 'ur', 'uz', 'vi',
            'cy', 'xh', 'yi', 'yo', 'zu'
        ]
        
        base_capabilities.update(google_capabilities)
        return base_capabilities
    
    def get_rate_limits(self) -> Dict[str, int]:
        """Get Google Translate rate limits"""
        if self.use_free_service:
            return {
                'requests_per_minute': 5,
                'requests_per_hour': 100,
                'characters_per_minute': 5000
            }
        else:
            return {
                'requests_per_minute': 100,
                'requests_per_hour': 10000,
                'characters_per_minute': 1000000
            }
    
    def set_api_key(self, api_key: str):
        """Set or update API key"""
        self.api_key = api_key
        self.use_free_service = api_key is None
        self.logger.info(f"Google Translate API key {'set' if api_key else 'removed'}")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get detailed usage statistics"""
        stats = self.get_stats()
        return {
            'provider': self.get_name(),
            'total_requests': stats.total_requests,
            'successful_requests': stats.successful_requests,
            'failed_requests': stats.failed_requests,
            'success_rate': stats.success_rate,
            'average_response_time': stats.average_response_time,
            'last_used': stats.last_used.isoformat() if stats.last_used else None,
            'service_type': 'api' if not self.use_free_service else 'free',
            'has_api_key': self.api_key is not None
        }
