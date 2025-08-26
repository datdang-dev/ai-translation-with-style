"""
Resiliency manager for coordinating fault tolerance policies
"""

import asyncio
from typing import Dict, Any, Optional, Callable, List
from services.models import HealthStatus, ResiliencyConfig
from services.common.logger import get_logger
from .server_fault_handler import ServerFaultHandler, RetryPolicy


class ResiliencyManager:
    """Manages resiliency policies and fault tolerance across services"""
    
    def __init__(self, 
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 circuit_breaker_threshold: int = 5,
                 circuit_breaker_timeout: float = 60.0):
        
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        
        self.logger = get_logger("ResiliencyManager")
        
        # Initialize fault handler
        self.fault_handler = ServerFaultHandler(
            max_retries=max_retries,
            retry_delay=retry_delay,
            circuit_breaker_threshold=circuit_breaker_threshold,
            circuit_breaker_timeout=circuit_breaker_timeout
        )
        
        # Provider-specific configurations
        self.provider_configs: Dict[str, ResiliencyConfig] = {}
        
        # Health monitoring
        self.health_status: Dict[str, HealthStatus] = {}
        
        # Fallback chains
        self.fallback_chains: Dict[str, List[str]] = {}
    
    def configure_provider(self, provider: str, config: ResiliencyConfig):
        """Configure resiliency for specific provider"""
        self.provider_configs[provider] = config
        
        # Set retry policy
        retry_policy = RetryPolicy(
            max_attempts=config.max_retries,
            base_delay=config.retry_delay,
            backoff_multiplier=config.retry_backoff_multiplier
        )
        self.fault_handler.set_retry_policy(provider, retry_policy)
        
        self.logger.info(f"Configured resiliency for {provider}")
    
    def set_fallback_chain(self, primary_provider: str, fallback_providers: List[str]):
        """Set fallback chain for a provider"""
        self.fallback_chains[primary_provider] = fallback_providers
        self.logger.info(f"Set fallback chain for {primary_provider}: {fallback_providers}")
    
    async def execute_with_retry(self, 
                               func: Callable,
                               provider: str = "default",
                               *args, 
                               **kwargs) -> Any:
        """Execute function with full resiliency (retry + circuit breaker + fallback)"""
        try:
            # Try primary execution with retry and circuit breaker
            return await self.fault_handler.execute_with_retry(func, provider, *args, **kwargs)
            
        except Exception as e:
            self.logger.warning(f"Primary execution failed for {provider}: {e}")
            
            # Try fallback providers if configured
            if provider in self.fallback_chains:
                return await self._execute_with_fallback(func, provider, *args, **kwargs)
            
            # No fallback available, re-raise exception
            raise
    
    async def _execute_with_fallback(self, 
                                   func: Callable, 
                                   failed_provider: str,
                                   *args, 
                                   **kwargs) -> Any:
        """Execute with fallback providers"""
        fallback_providers = self.fallback_chains.get(failed_provider, [])
        
        for fallback_provider in fallback_providers:
            try:
                self.logger.info(f"Trying fallback provider: {fallback_provider}")
                
                # Update provider context if the function expects it
                # This is a simple approach - in practice you might need more sophisticated parameter handling
                if 'provider' in kwargs:
                    kwargs['provider'] = fallback_provider
                
                return await self.fault_handler.execute_with_retry(func, fallback_provider, *args, **kwargs)
                
            except Exception as e:
                self.logger.warning(f"Fallback provider {fallback_provider} also failed: {e}")
                continue
        
        # All fallbacks failed
        raise Exception(f"All providers failed including fallbacks for {failed_provider}")
    
    def update_health_status(self, provider: str, status: HealthStatus):
        """Update provider health status"""
        self.health_status[provider] = status
        
        # Log health changes
        if status.is_healthy:
            self.logger.debug(f"Provider {provider} is healthy")
        else:
            self.logger.warning(f"Provider {provider} is unhealthy: {status.message}")
    
    def get_provider_health(self) -> Dict[str, HealthStatus]:
        """Get health status of all providers"""
        return self.health_status.copy()
    
    def is_provider_healthy(self, provider: str) -> bool:
        """Check if provider is healthy"""
        health = self.health_status.get(provider)
        return health is not None and health.is_healthy
    
    def get_fault_handler(self) -> ServerFaultHandler:
        """Get the fault handler instance"""
        return self.fault_handler
    
    def get_circuit_breaker_status(self, provider: str = None) -> Dict[str, Any]:
        """Get circuit breaker status"""
        if provider:
            return self.fault_handler.get_circuit_breaker_status(provider)
        else:
            # Get status for all providers
            all_status = {}
            for p in self.provider_configs.keys():
                all_status[p] = self.fault_handler.get_circuit_breaker_status(p)
            return all_status
    
    def reset_circuit_breaker(self, provider: str):
        """Reset circuit breaker for provider"""
        self.fault_handler.reset_circuit_breaker(provider)
        self.logger.info(f"Circuit breaker reset for {provider}")
    
    def get_resiliency_stats(self) -> Dict[str, Any]:
        """Get comprehensive resiliency statistics"""
        fault_stats = self.fault_handler.get_fault_statistics()
        
        stats = {
            'fault_statistics': fault_stats,
            'provider_configs': {
                provider: {
                    'max_retries': config.max_retries,
                    'retry_delay': config.retry_delay,
                    'circuit_breaker_threshold': config.circuit_breaker_threshold,
                    'circuit_breaker_timeout': config.circuit_breaker_timeout
                }
                for provider, config in self.provider_configs.items()
            },
            'fallback_chains': self.fallback_chains,
            'health_status': {
                provider: {
                    'is_healthy': health.is_healthy,
                    'message': health.message,
                    'last_check': health.last_check.isoformat(),
                    'response_time': health.response_time
                }
                for provider, health in self.health_status.items()
            }
        }
        
        return stats
    
    def configure_default_policies(self):
        """Configure default resiliency policies for common providers"""
        # OpenRouter configuration
        openrouter_config = ResiliencyConfig(
            max_retries=3,
            retry_delay=2.0,
            retry_backoff_multiplier=2.0,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=60.0
        )
        self.configure_provider("openrouter", openrouter_config)
        
        # Google Translate configuration
        google_config = ResiliencyConfig(
            max_retries=2,
            retry_delay=1.0,
            retry_backoff_multiplier=1.5,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=30.0
        )
        self.configure_provider("google_translate", google_config)
        
        # Set up fallback chain: OpenRouter -> Google Translate
        self.set_fallback_chain("openrouter", ["google_translate"])
        self.set_fallback_chain("google_translate", ["openrouter"])
        
        self.logger.info("Default resiliency policies configured")
    
    async def test_provider_resiliency(self, provider: str) -> Dict[str, Any]:
        """Test resiliency configuration for a provider"""
        results = {
            'provider': provider,
            'circuit_breaker_status': self.get_circuit_breaker_status(provider),
            'health_status': self.health_status.get(provider),
            'configuration': self.provider_configs.get(provider),
            'fallback_chain': self.fallback_chains.get(provider, [])
        }
        
        return results
    
    def enable_provider(self, provider: str):
        """Enable provider (reset circuit breaker and clear failures)"""
        self.fault_handler.reset_circuit_breaker(provider)
        self.fault_handler.reset_fault_stats(provider)
        
        # Set healthy status
        self.health_status[provider] = HealthStatus.healthy(f"Provider {provider} manually enabled")
        
        self.logger.info(f"Provider {provider} enabled")
    
    def disable_provider(self, provider: str, reason: str = "Manually disabled"):
        """Disable provider (mark as unhealthy)"""
        self.health_status[provider] = HealthStatus.unhealthy(reason)
        self.logger.info(f"Provider {provider} disabled: {reason}")
    
    def get_provider_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations for provider configuration based on statistics"""
        recommendations = []
        fault_stats = self.fault_handler.get_fault_statistics()
        
        for provider, stats in fault_stats.get('providers', {}).items():
            provider_recommendations = []
            
            # Check failure patterns
            total_failures = sum(stats.values())
            if total_failures > 10:
                rate_limit_failures = stats.get('rate_limit', 0)
                if rate_limit_failures / total_failures > 0.5:
                    provider_recommendations.append("Consider increasing retry delay for rate limits")
                
                timeout_failures = stats.get('timeout', 0)
                if timeout_failures / total_failures > 0.3:
                    provider_recommendations.append("Consider increasing request timeout")
            
            # Check circuit breaker status
            cb_status = fault_stats.get('circuit_breakers', {}).get(provider, {})
            if cb_status.get('state') == 'open':
                provider_recommendations.append("Circuit breaker is open - check provider health")
            elif cb_status.get('failure_count', 0) > 2:
                provider_recommendations.append("High failure count - monitor provider closely")
            
            if provider_recommendations:
                recommendations.append({
                    'provider': provider,
                    'recommendations': provider_recommendations,
                    'total_failures': total_failures,
                    'circuit_breaker_state': cb_status.get('state', 'unknown')
                })
        
        return recommendations