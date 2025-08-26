"""
Provider orchestrator for managing multiple translation providers
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from services.models import (
    TranslationRequest, TranslationResult, HealthStatus, ProviderStats, 
    ProviderType, ProviderError
)
from services.common.logger import get_logger
from .base_provider import ITranslationProvider


class ProviderOrchestrator:
    """Orchestrates multiple translation providers with health-based selection"""
    
    def __init__(self):
        self.providers: Dict[str, ITranslationProvider] = {}
        self.health_status: Dict[str, HealthStatus] = {}
        self.logger = get_logger("ProviderOrchestrator")
        self.default_provider = None
        self._health_check_interval = 300  # 5 minutes
        self._last_health_check = 0
    
    def register_provider(self, provider: ITranslationProvider):
        """Register a new translation provider"""
        name = provider.get_name()
        self.providers[name] = provider
        self.health_status[name] = HealthStatus.healthy("Provider registered")
        self.logger.info(f"Registered provider: {name}")
        
        # Set first provider as default
        if self.default_provider is None:
            self.default_provider = name
    
    def unregister_provider(self, provider_name: str):
        """Unregister a provider"""
        if provider_name in self.providers:
            del self.providers[provider_name]
            del self.health_status[provider_name]
            self.logger.info(f"Unregistered provider: {provider_name}")
            
            # Update default if needed
            if self.default_provider == provider_name:
                self.default_provider = next(iter(self.providers.keys())) if self.providers else None
    
    def get_provider(self, name: str) -> Optional[ITranslationProvider]:
        """Get provider by name"""
        return self.providers.get(name)
    
    def list_providers(self) -> List[str]:
        """Get list of registered provider names"""
        return list(self.providers.keys())
    
    def get_available_providers(self) -> List[str]:
        """Get list of healthy/available providers"""
        current_time = time.time()
        
        # Update health status if needed
        if current_time - self._last_health_check > self._health_check_interval:
            asyncio.create_task(self._update_health_status())
        
        available = []
        for name, health in self.health_status.items():
            if health.is_healthy and name in self.providers:
                provider = self.providers[name]
                if hasattr(provider, 'is_enabled') and provider.is_enabled():
                    available.append(name)
        
        return available
    
    def select_provider(self, request: TranslationRequest = None) -> str:
        """Select best provider for request"""
        # If specific provider requested
        if request and request.provider != ProviderType.AUTO:
            provider_name = request.provider.value
            if provider_name in self.providers and self._is_provider_available(provider_name):
                return provider_name
            else:
                self.logger.warning(f"Requested provider {provider_name} not available, selecting automatically")
        
        # Get available providers
        available_providers = self.get_available_providers()
        
        if not available_providers:
            if self.providers:
                # Return default if no healthy providers
                return self.default_provider or next(iter(self.providers.keys()))
            else:
                raise ProviderError("No providers available")
        
        # Select provider based on priority and health
        best_provider = self._select_best_provider(available_providers)
        return best_provider
    
    def _select_best_provider(self, available_providers: List[str]) -> str:
        """Select best provider from available ones"""
        if not available_providers:
            raise ProviderError("No available providers")
        
        # Score providers based on multiple factors
        scored_providers = []
        
        for provider_name in available_providers:
            provider = self.providers[provider_name]
            health = self.health_status[provider_name]
            stats = provider.get_stats() if hasattr(provider, 'get_stats') else None
            
            score = self._calculate_provider_score(provider, health, stats)
            scored_providers.append((provider_name, score))
        
        # Sort by score (higher is better) and return best
        scored_providers.sort(key=lambda x: x[1], reverse=True)
        return scored_providers[0][0]
    
    def _calculate_provider_score(self, 
                                 provider: ITranslationProvider, 
                                 health: HealthStatus, 
                                 stats: ProviderStats) -> float:
        """Calculate provider score for selection"""
        score = 0.0
        
        # Health score (0-40 points)
        if health.is_healthy:
            score += 40
            # Bonus for good response time
            if health.response_time < 1.0:
                score += 10
            elif health.response_time < 3.0:
                score += 5
        
        # Priority score (0-30 points) - lower priority number = higher score
        if hasattr(provider, 'get_priority'):
            priority = provider.get_priority()
            score += max(0, 30 - (priority * 5))
        
        # Success rate score (0-20 points)
        if stats and stats.total_requests > 0:
            success_rate = stats.success_rate / 100.0  # Convert to 0-1
            score += success_rate * 20
        else:
            score += 15  # Default score for new providers
        
        # Response time score (0-10 points)
        if stats and stats.average_response_time > 0:
            # Better score for faster response times
            if stats.average_response_time < 1.0:
                score += 10
            elif stats.average_response_time < 3.0:
                score += 7
            elif stats.average_response_time < 5.0:
                score += 4
        else:
            score += 5  # Default for providers without stats
        
        return score
    
    def _is_provider_available(self, provider_name: str) -> bool:
        """Check if provider is available"""
        if provider_name not in self.providers:
            return False
        
        health = self.health_status.get(provider_name)
        if not health or not health.is_healthy:
            return False
        
        provider = self.providers[provider_name]
        if hasattr(provider, 'is_enabled') and not provider.is_enabled():
            return False
        
        return True
    
    async def translate(self, texts: List[str], target_lang: str, source_lang: str = "auto") -> List[str]:
        """Translate using best available provider"""
        if not texts:
            return []
        
        # Select provider
        provider_name = self.select_provider()
        provider = self.providers[provider_name]
        
        try:
            self.logger.info(f"Translating {len(texts)} texts using {provider_name}")
            result = await provider.translate(texts, target_lang, source_lang)
            self.logger.info(f"Translation completed successfully using {provider_name}")
            return result
            
        except Exception as e:
            self.logger.error(f"Translation failed with {provider_name}: {e}")
            
            # Try fallback provider
            return await self._try_fallback_translation(texts, target_lang, source_lang, provider_name)
    
    async def _try_fallback_translation(self, 
                                      texts: List[str], 
                                      target_lang: str, 
                                      source_lang: str,
                                      failed_provider: str) -> List[str]:
        """Try translation with fallback providers"""
        available_providers = [p for p in self.get_available_providers() if p != failed_provider]
        
        if not available_providers:
            raise ProviderError(f"All providers failed, no fallback available")
        
        # Try each available provider
        for provider_name in available_providers:
            try:
                provider = self.providers[provider_name]
                self.logger.info(f"Trying fallback provider: {provider_name}")
                result = await provider.translate(texts, target_lang, source_lang)
                self.logger.info(f"Fallback translation successful with {provider_name}")
                return result
                
            except Exception as e:
                self.logger.warning(f"Fallback provider {provider_name} also failed: {e}")
                continue
        
        raise ProviderError("All providers failed to translate")
    
    async def _update_health_status(self):
        """Update health status of all providers"""
        self._last_health_check = time.time()
        
        health_checks = []
        for name, provider in self.providers.items():
            health_checks.append(self._check_provider_health(name, provider))
        
        if health_checks:
            await asyncio.gather(*health_checks, return_exceptions=True)
    
    async def _check_provider_health(self, name: str, provider: ITranslationProvider):
        """Check health of a single provider"""
        try:
            health = await provider.health_check()
            self.health_status[name] = health
            
            if health.is_healthy:
                self.logger.debug(f"Provider {name} health check passed")
            else:
                self.logger.warning(f"Provider {name} health check failed: {health.message}")
                
        except Exception as e:
            self.logger.error(f"Health check error for {name}: {e}")
            self.health_status[name] = HealthStatus.unhealthy(f"Health check failed: {e}")
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all providers"""
        status = {}
        
        for name, provider in self.providers.items():
            health = self.health_status.get(name, HealthStatus.unhealthy("No health data"))
            stats = provider.get_stats() if hasattr(provider, 'get_stats') else None
            
            provider_status = {
                'name': name,
                'enabled': provider.is_enabled() if hasattr(provider, 'is_enabled') else True,
                'healthy': health.is_healthy,
                'health_message': health.message,
                'last_health_check': health.last_check.isoformat(),
                'response_time': health.response_time,
                'capabilities': provider.get_capabilities(),
                'rate_limits': provider.get_rate_limits()
            }
            
            if stats:
                provider_status.update({
                    'total_requests': stats.total_requests,
                    'success_rate': stats.success_rate,
                    'average_response_time': stats.average_response_time,
                    'last_used': stats.last_used.isoformat() if stats.last_used else None
                })
            
            status[name] = provider_status
        
        return status
    
    def get_health_status(self) -> Dict[str, HealthStatus]:
        """Get health status of all providers"""
        return self.health_status.copy()
    
    async def force_health_check(self):
        """Force immediate health check of all providers"""
        await self._update_health_status()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        total_providers = len(self.providers)
        healthy_providers = sum(1 for h in self.health_status.values() if h.is_healthy)
        
        return {
            'total_providers': total_providers,
            'healthy_providers': healthy_providers,
            'available_providers': len(self.get_available_providers()),
            'default_provider': self.default_provider,
            'last_health_check': self._last_health_check,
            'provider_names': list(self.providers.keys())
        }
