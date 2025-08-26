"""
Enhanced OpenRouter client for the new architecture
"""

import json
import aiohttp
from typing import List, Dict, Any, Optional
from services.models import HealthStatus, ProviderError
from services.common.logger import get_logger
from .base_provider import BaseTranslationProvider


class OpenRouterClient(BaseTranslationProvider):
    """Enhanced OpenRouter client with translation-specific interface"""
    
    def __init__(self, api_key: str, base_url: str = None, config: Dict[str, Any] = None):
        super().__init__("openrouter", config)
        self.api_key = api_key
        self.base_url = base_url or "https://openrouter.ai/api/v1/chat/completions"
        self.logger = get_logger("OpenRouterClient")
        
        # Default model and parameters
        self.model = self.config.get('model', 'anthropic/claude-3.5-sonnet')
        self.max_tokens = self.config.get('max_tokens', 4000)
        self.temperature = self.config.get('temperature', 0.3)
    
    async def translate(self, texts: List[str], target_lang: str, source_lang: str = "auto") -> List[str]:
        """Translate list of texts using OpenRouter"""
        self._validate_texts(texts)
        self._validate_languages(source_lang, target_lang)
        
        try:
            # Build translation prompt
            prompt = self._build_translation_prompt(texts, target_lang, source_lang)
            
            # Make API request
            payload = self._build_payload(prompt)
            response = await self._send_request(payload)
            
            # Parse response
            translated_texts = self._parse_translation_response(response, len(texts))
            
            return translated_texts
            
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            raise ProviderError(f"OpenRouter translation failed: {e}")
    
    def _build_translation_prompt(self, texts: List[str], target_lang: str, source_lang: str) -> str:
        """Build translation prompt for the model"""
        source_desc = f"from {source_lang}" if source_lang != "auto" else ""
        
        prompt = f"""Translate the following texts to {target_lang} {source_desc}. 
Return ONLY the translations in the same order, one per line, without any additional text or explanations.

Input texts:
"""
        
        for i, text in enumerate(texts):
            prompt += f"{i+1}. {text}\n"
        
        prompt += "\nTranslations:"
        
        return prompt
    
    def _build_payload(self, prompt: str) -> Dict[str, Any]:
        """Build API request payload"""
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False
        }
    
    async def _send_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to OpenRouter API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/ai-translation",
            "X-Title": "AI Translation Service"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status == 429:
                        raise ProviderError("Rate limit exceeded", error_code="RATE_LIMIT")
                    elif response.status == 401:
                        raise ProviderError("Authentication failed", error_code="AUTH_ERROR")
                    elif response.status >= 500:
                        raise ProviderError("Server error", error_code="SERVER_ERROR")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise ProviderError(f"API error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    return result
                    
            except aiohttp.ClientError as e:
                raise ProviderError(f"Network error: {e}", error_code="NETWORK_ERROR")
            except Exception as e:
                raise ProviderError(f"Request failed: {e}")
    
    def _parse_translation_response(self, response: Dict[str, Any], expected_count: int) -> List[str]:
        """Parse OpenRouter response and extract translations"""
        try:
            # Extract content from response
            choices = response.get('choices', [])
            if not choices:
                raise ProviderError("No response choices received")
            
            content = choices[0].get('message', {}).get('content', '')
            if not content:
                raise ProviderError("Empty response content")
            
            # Parse translations from content
            translations = self._extract_translations_from_content(content)
            
            # Validate translation count
            if len(translations) != expected_count:
                self.logger.warning(
                    f"Translation count mismatch: expected {expected_count}, got {len(translations)}"
                )
                # Pad with original texts if needed
                while len(translations) < expected_count:
                    translations.append("")
            
            return translations[:expected_count]
            
        except Exception as e:
            raise ProviderError(f"Failed to parse translation response: {e}")
    
    def _extract_translations_from_content(self, content: str) -> List[str]:
        """Extract individual translations from response content"""
        lines = content.strip().split('\n')
        translations = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove numbering (1. 2. etc.)
            if line and line[0].isdigit() and '.' in line:
                parts = line.split('.', 1)
                if len(parts) > 1:
                    line = parts[1].strip()
            
            # Remove common prefixes
            for prefix in ['Translation:', 'Answer:', '- ']:
                if line.startswith(prefix):
                    line = line[len(prefix):].strip()
                    break
            
            if line:
                translations.append(line)
        
        return translations
    
    async def health_check(self) -> HealthStatus:
        """Check OpenRouter service health"""
        try:
            import time
            start_time = time.time()
            
            # Simple translation test
            test_texts = ["Hello"]
            result = await self.translate(test_texts, "es", "en")
            
            response_time = time.time() - start_time
            
            if result and len(result) > 0 and result[0].strip():
                return HealthStatus.healthy(
                    "OpenRouter service operational", 
                    response_time=response_time
                )
            else:
                return HealthStatus.unhealthy("OpenRouter returned empty translation")
                
        except ProviderError as e:
            return HealthStatus.unhealthy(f"OpenRouter health check failed: {e.message}")
        except Exception as e:
            return HealthStatus.unhealthy(f"OpenRouter health check error: {e}")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get OpenRouter-specific capabilities"""
        base_capabilities = super().get_capabilities()
        
        # OpenRouter specific capabilities
        openrouter_capabilities = {
            'max_text_length': 8000,  # Conservative estimate
            'max_batch_size': 50,     # Reasonable batch size
            'supports_auto_detect': True,
            'supported_languages': [
                'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh',
                'ar', 'hi', 'th', 'vi', 'tr', 'pl', 'nl', 'sv', 'da', 'no'
            ],
            'model': self.model,
            'provider_type': 'llm',
            'supports_context': True
        }
        
        base_capabilities.update(openrouter_capabilities)
        return base_capabilities
    
    def get_rate_limits(self) -> Dict[str, int]:
        """Get OpenRouter rate limits"""
        return {
            'requests_per_minute': 20,
            'requests_per_hour': 200,
            'characters_per_minute': 100000,
            'tokens_per_minute': 50000
        }
    
    def update_api_key(self, new_api_key: str):
        """Update API key for key rotation"""
        self.api_key = new_api_key
        self.logger.info("API key updated")
    
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
            'model': self.model,
            'api_key_prefix': self.api_key[:8] + "..." if self.api_key else None
        }