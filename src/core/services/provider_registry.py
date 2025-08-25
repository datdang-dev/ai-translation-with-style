"""Provider registry for managing translation providers"""

import asyncio
from typing import Dict, List, Optional, Type, Callable
from datetime import datetime, timezone

from ..interfaces import TranslationProvider, HealthCheck
from ..models import ProvidersConfig, ProviderConfig
from ...infrastructure.observability import get_logger, get_metrics


class ProviderNotFoundError(Exception):
    """Raised when a requested provider is not found"""
    pass


class ProviderRegistry:
    """
    Registry for managing translation providers.
    
    Features:
    - Dynamic provider registration
    - Health monitoring
    - Fallback provider selection
    - Load balancing
    - Provider lifecycle management
    """
    
    def __init__(self, config: Optional[ProvidersConfig] = None):
        """
        Initialize provider registry.
        
        Args:
            config: Providers configuration
        """
        self.config = config or ProvidersConfig()
        self.logger = get_logger("provider_registry")
        self.metrics = get_metrics()
        
        # Provider storage
        self._providers: Dict[str, TranslationProvider] = {}
        self._provider_factories: Dict[str, Callable[[ProviderConfig], TranslationProvider]] = {}
        self._health_checks: Dict[str, HealthCheck] = {}
        self._last_health_check: Dict[str, datetime] = {}
        
        # Provider selection
        self._current_provider_index = 0
        self._lock = asyncio.Lock()
    
    def register_provider_factory(
        self, 
        provider_type: str, 
        factory: Callable[[ProviderConfig], TranslationProvider]
    ) -> None:
        """
        Register a factory for creating providers of a specific type.
        
        Args:
            provider_type: Type identifier (e.g., "openrouter", "openai")
            factory: Factory function that creates provider instances
        """
        self._provider_factories[provider_type] = factory
        self.logger.info(f"Registered provider factory for type: {provider_type}")
    
    async def initialize_providers(self) -> None:
        """Initialize all configured providers"""
        if not self.config.providers:
            self.logger.warning("No providers configured")
            return
        
        for provider_config in self.config.providers:
            try:
                await self._create_provider(provider_config)
            except Exception as e:
                self.logger.error(
                    f"Failed to initialize provider {provider_config.name}",
                    error=str(e),
                    provider_type=provider_config.type
                )
    
    async def _create_provider(self, config: ProviderConfig) -> TranslationProvider:
        """Create a provider instance from configuration"""
        if config.type not in self._provider_factories:
            raise ValueError(f"No factory registered for provider type: {config.type}")
        
        factory = self._provider_factories[config.type]
        provider = factory(config)
        
        # Store provider
        self._providers[config.name] = provider
        
        # Create health check if provider supports it
        if hasattr(provider, 'health_check'):
            self._health_checks[config.name] = provider
        
        self.logger.info(
            f"Created provider {config.name}",
            provider_type=config.type,
            enabled=config.enabled
        )
        
        return provider
    
    async def get_provider(self, name: str) -> TranslationProvider:
        """
        Get a specific provider by name.
        
        Args:
            name: Provider name
            
        Returns:
            TranslationProvider instance
            
        Raises:
            ProviderNotFoundError: If provider is not found or not healthy
        """
        async with self._lock:
            if name not in self._providers:
                raise ProviderNotFoundError(f"Provider '{name}' not found")
            
            provider = self._providers[name]
            
            # Check if provider is enabled
            if not provider.config.enabled:
                raise ProviderNotFoundError(f"Provider '{name}' is disabled")
            
            # Check health if needed
            if await self._should_check_health(name):
                is_healthy = await self._check_provider_health(name)
                if not is_healthy:
                    raise ProviderNotFoundError(f"Provider '{name}' is unhealthy")
            
            return provider
    
    async def get_default_provider(self) -> TranslationProvider:
        """
        Get the default provider.
        
        Returns:
            Default TranslationProvider instance
            
        Raises:
            ProviderNotFoundError: If no default provider is configured or available
        """
        if self.config.default_provider:
            return await self.get_provider(self.config.default_provider)
        
        # Fallback to first healthy provider
        healthy_providers = await self.get_healthy_providers()
        if not healthy_providers:
            raise ProviderNotFoundError("No healthy providers available")
        
        return healthy_providers[0]
    
    async def get_healthy_providers(self) -> List[TranslationProvider]:
        """
        Get all healthy providers.
        
        Returns:
            List of healthy providers sorted by priority
        """
        healthy_providers = []
        
        for name, provider in self._providers.items():
            if not provider.config.enabled:
                continue
            
            # Check health
            if await self._should_check_health(name):
                is_healthy = await self._check_provider_health(name)
                if not is_healthy:
                    continue
            
            healthy_providers.append(provider)
        
        # Sort by priority (lower number = higher priority)
        healthy_providers.sort(key=lambda p: p.config.priority)
        
        return healthy_providers
    
    async def get_fallback_providers(self, exclude: Optional[str] = None) -> List[TranslationProvider]:
        """
        Get providers in fallback order.
        
        Args:
            exclude: Provider name to exclude from fallback list
            
        Returns:
            List of fallback providers
        """
        if not self.config.enable_fallback:
            return []
        
        fallback_providers = []
        
        # Use configured fallback order if available
        if self.config.fallback_order:
            for provider_name in self.config.fallback_order:
                if exclude and provider_name == exclude:
                    continue
                
                try:
                    provider = await self.get_provider(provider_name)
                    fallback_providers.append(provider)
                except ProviderNotFoundError:
                    # Provider not available, skip
                    continue
        else:
            # Use all healthy providers except excluded one
            healthy_providers = await self.get_healthy_providers()
            fallback_providers = [
                p for p in healthy_providers 
                if not exclude or p.name != exclude
            ]
        
        return fallback_providers
    
    async def select_best_provider(
        self, 
        exclude: Optional[List[str]] = None
    ) -> Optional[TranslationProvider]:
        """
        Select the best available provider using load balancing.
        
        Args:
            exclude: List of provider names to exclude
            
        Returns:
            Best available provider or None
        """
        exclude = exclude or []
        healthy_providers = await self.get_healthy_providers()
        
        # Filter out excluded providers
        available_providers = [
            p for p in healthy_providers 
            if p.name not in exclude
        ]
        
        if not available_providers:
            return None
        
        # Simple round-robin selection
        async with self._lock:
            provider = available_providers[self._current_provider_index % len(available_providers)]
            self._current_provider_index = (self._current_provider_index + 1) % len(available_providers)
            return provider
    
    async def _should_check_health(self, provider_name: str) -> bool:
        """Check if we should perform a health check for a provider"""
        if provider_name not in self._health_checks:
            return False
        
        last_check = self._last_health_check.get(provider_name)
        if last_check is None:
            return True
        
        # Check health every 60 seconds
        now = datetime.now(timezone.utc)
        return (now - last_check).total_seconds() > 60
    
    async def _check_provider_health(self, provider_name: str) -> bool:
        """Check the health of a specific provider"""
        if provider_name not in self._health_checks:
            return True  # Assume healthy if no health check available
        
        try:
            health_check = self._health_checks[provider_name]
            is_healthy = await health_check.health_check()
            
            # Update health check timestamp
            self._last_health_check[provider_name] = datetime.now(timezone.utc)
            
            # Record metrics
            self.metrics.record_provider_health(provider_name, is_healthy)
            
            if is_healthy:
                self.logger.debug(f"Provider {provider_name} is healthy")
            else:
                self.logger.warning(f"Provider {provider_name} failed health check")
            
            return is_healthy
            
        except Exception as e:
            self.logger.error(
                f"Health check failed for provider {provider_name}",
                error=str(e)
            )
            
            # Record unhealthy status
            self.metrics.record_provider_health(provider_name, False)
            return False
    
    async def run_health_checks(self) -> Dict[str, bool]:
        """
        Run health checks for all providers.
        
        Returns:
            Dictionary mapping provider names to health status
        """
        health_status = {}
        
        for provider_name in self._providers:
            if provider_name in self._health_checks:
                health_status[provider_name] = await self._check_provider_health(provider_name)
            else:
                health_status[provider_name] = True  # Assume healthy
        
        return health_status
    
    def get_provider_info(self) -> Dict[str, Dict]:
        """Get information about all registered providers"""
        info = {}
        
        for name, provider in self._providers.items():
            info[name] = {
                "name": provider.name,
                "type": provider.provider_type,
                "enabled": provider.config.enabled,
                "priority": provider.config.priority,
                "models": [model.name for model in provider.config.models],
                "default_model": provider.config.default_model,
                "has_health_check": name in self._health_checks
            }
        
        return info
    
    async def close_all_providers(self) -> None:
        """Close all providers and clean up resources"""
        for name, provider in self._providers.items():
            try:
                await provider.close()
                self.logger.debug(f"Closed provider {name}")
            except Exception as e:
                self.logger.error(f"Error closing provider {name}: {e}")
        
        self._providers.clear()
        self._health_checks.clear()
        self._last_health_check.clear()
        
        self.logger.info("All providers closed")
    
    def __len__(self) -> int:
        """Get number of registered providers"""
        return len(self._providers)
    
    def __contains__(self, provider_name: str) -> bool:
        """Check if provider is registered"""
        return provider_name in self._providers