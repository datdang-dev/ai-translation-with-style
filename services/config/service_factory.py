"""
Service factory for dependency injection and service creation
"""

from typing import Dict, Any, Optional
from services.config.configuration_manager import ConfigurationManager
from services.standardizer import StandardizerService
from services.providers import (
    ProviderOrchestrator, OpenRouterClient, GoogleTranslateClient
)
from services.infrastructure import CacheService, HealthMonitor, ValidatorService
from services.resiliency import ResiliencyManager
from services.middleware import RequestManager, TranslationManager
from services.common.logger import get_logger


class ServiceFactory:
    """Factory for creating and configuring services with dependency injection"""
    
    def __init__(self, config_manager: ConfigurationManager = None):
        self.config_manager = config_manager or ConfigurationManager()
        self.logger = get_logger("ServiceFactory")
        
        # Service instances (singleton pattern)
        self._instances: Dict[str, Any] = {}
        
        # Validate configuration
        if not self.config_manager.validate_config():
            self.logger.warning("Configuration validation failed, some services may not work correctly")
    
    def get_standardizer_service(self) -> StandardizerService:
        """Get or create StandardizerService"""
        if 'standardizer_service' not in self._instances:
            self._instances['standardizer_service'] = StandardizerService()
            self.logger.info("Created StandardizerService")
        
        return self._instances['standardizer_service']
    
    def get_cache_service(self) -> Optional[CacheService]:
        """Get or create CacheService"""
        if 'cache_service' not in self._instances:
            cache_config = self.config_manager.get_cache_config()
            
            if cache_config.enabled:
                self._instances['cache_service'] = CacheService(cache_config)
                self.logger.info(f"Created CacheService with {cache_config.backend} backend")
            else:
                self._instances['cache_service'] = None
                self.logger.info("Cache service disabled")
        
        return self._instances['cache_service']
    
    def get_validator_service(self) -> ValidatorService:
        """Get or create ValidatorService"""
        if 'validator_service' not in self._instances:
            self._instances['validator_service'] = ValidatorService()
            self.logger.info("Created ValidatorService")
        
        return self._instances['validator_service']
    
    def get_health_monitor(self) -> HealthMonitor:
        """Get or create HealthMonitor"""
        if 'health_monitor' not in self._instances:
            self._instances['health_monitor'] = HealthMonitor()
            self.logger.info("Created HealthMonitor")
        
        return self._instances['health_monitor']
    
    def get_resiliency_manager(self) -> ResiliencyManager:
        """Get or create ResiliencyManager"""
        if 'resiliency_manager' not in self._instances:
            resiliency_config = self.config_manager.get_resiliency_config()
            
            resiliency_manager = ResiliencyManager(
                max_retries=resiliency_config.max_retries,
                retry_delay=resiliency_config.retry_delay,
                circuit_breaker_threshold=resiliency_config.circuit_breaker_threshold,
                circuit_breaker_timeout=resiliency_config.circuit_breaker_timeout
            )
            
            # Configure default policies
            resiliency_manager.configure_default_policies()
            
            self._instances['resiliency_manager'] = resiliency_manager
            self.logger.info("Created ResiliencyManager with default policies")
        
        return self._instances['resiliency_manager']
    
    def get_provider_orchestrator(self) -> ProviderOrchestrator:
        """Get or create ProviderOrchestrator with all configured providers"""
        if 'provider_orchestrator' not in self._instances:
            orchestrator = ProviderOrchestrator()
            
            # Create and register providers
            provider_configs = self.config_manager.get_provider_configs()
            api_keys = self.config_manager.get_api_keys()
            
            for name, config in provider_configs.items():
                if not config.enabled:
                    self.logger.info(f"Provider {name} is disabled, skipping")
                    continue
                
                try:
                    provider = self._create_provider(name, config, api_keys)
                    if provider:
                        orchestrator.register_provider(provider)
                        self.logger.info(f"Registered provider: {name}")
                
                except Exception as e:
                    self.logger.error(f"Failed to create provider {name}: {e}")
            
            self._instances['provider_orchestrator'] = orchestrator
            self.logger.info(f"Created ProviderOrchestrator with {len(orchestrator.list_providers())} providers")
        
        return self._instances['provider_orchestrator']
    
    def _create_provider(self, name: str, config: Any, api_keys: Dict[str, str]):
        """Create a specific provider instance"""
        if name == 'openrouter':
            api_key = api_keys.get('openrouter') or api_keys.get('openrouter_api_key')
            if not api_key:
                self.logger.warning("OpenRouter API key not found, provider will not be available")
                return None
            
            # Get preset configuration for this provider
            preset_name = config.config.get('preset', 'preset_translation')
            preset_config = self.config_manager.get_preset(preset_name)
            
            return OpenRouterClient(
                api_key=api_key,
                config=config.config,
                preset_config=preset_config
            )
        
        elif name == 'google_translate':
            api_key = api_keys.get('google_translate') or api_keys.get('google_api_key')
            # Google Translate can work without API key (free service)
            
            return GoogleTranslateClient(
                api_key=api_key,
                config=config.config
            )
        
        else:
            self.logger.warning(f"Unknown provider type: {name}")
            return None
    
    def get_request_manager(self) -> RequestManager:
        """Get or create RequestManager"""
        if 'request_manager' not in self._instances:
            processing_config = self.config_manager.get_processing_config()
            
            request_manager = RequestManager(
                standardizer_service=self.get_standardizer_service(),
                provider_orchestrator=self.get_provider_orchestrator(),
                cache_service=self.get_cache_service(),
                validator_service=self.get_validator_service(),
                max_workers=processing_config.get('max_workers', 10)
            )
            
            self._instances['request_manager'] = request_manager
            self.logger.info("Created RequestManager")
        
        return self._instances['request_manager']
    
    def get_translation_manager(self) -> TranslationManager:
        """Get or create TranslationManager"""
        if 'translation_manager' not in self._instances:
            processing_config = self.config_manager.get_processing_config()
            
            translation_manager = TranslationManager(
                request_manager=self.get_request_manager(),
                resiliency_manager=self.get_resiliency_manager(),
                batch_size=processing_config.get('batch_size', 10),
                max_concurrent=processing_config.get('max_concurrent', 3)
            )
            
            self._instances['translation_manager'] = translation_manager
            self.logger.info("Created TranslationManager")
        
        return self._instances['translation_manager']
    
    def setup_health_monitoring(self):
        """Set up health monitoring for all providers"""
        health_monitor = self.get_health_monitor()
        provider_orchestrator = self.get_provider_orchestrator()
        
        # Register health checks for all providers
        for provider_name in provider_orchestrator.list_providers():
            provider = provider_orchestrator.get_provider(provider_name)
            if provider:
                health_monitor.register_health_check(
                    provider_name,
                    provider.health_check
                )
        
        self.logger.info(f"Set up health monitoring for {len(provider_orchestrator.list_providers())} providers")
    
    async def start_health_monitoring(self):
        """Start continuous health monitoring"""
        health_monitor = self.get_health_monitor()
        await health_monitor.start_monitoring()
        self.logger.info("Started health monitoring")
    
    async def stop_health_monitoring(self):
        """Stop health monitoring"""
        if 'health_monitor' in self._instances:
            health_monitor = self._instances['health_monitor']
            await health_monitor.stop_monitoring()
            self.logger.info("Stopped health monitoring")
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services"""
        status = {
            'configuration_valid': self.config_manager.validate_config(),
            'services_created': list(self._instances.keys()),
            'total_services': len(self._instances)
        }
        
        # Add specific service statuses
        if 'provider_orchestrator' in self._instances:
            orchestrator = self._instances['provider_orchestrator']
            status['providers'] = {
                'total': len(orchestrator.list_providers()),
                'available': len(orchestrator.get_available_providers()),
                'providers': orchestrator.list_providers()
            }
        
        if 'cache_service' in self._instances and self._instances['cache_service']:
            cache_service = self._instances['cache_service']
            status['cache'] = cache_service.get_stats()
        
        if 'translation_manager' in self._instances:
            translation_manager = self._instances['translation_manager']
            status['translation_manager'] = translation_manager.get_status()
        
        return status
    
    def create_default_config_file(self, config_path: str = None):
        """Create a default configuration file"""
        if config_path is None:
            config_path = self.config_manager.config_path
        
        # Export default configuration
        self.config_manager.export_config(config_path, 'yaml')
        self.logger.info(f"Created default configuration file: {config_path}")
    
    def reset_services(self):
        """Reset all service instances (for testing)"""
        self._instances.clear()
        self.logger.info("All service instances reset")
    
    def get_instance(self, service_name: str) -> Optional[Any]:
        """Get service instance by name"""
        return self._instances.get(service_name)
    
    def register_instance(self, service_name: str, instance: Any):
        """Register a service instance manually"""
        self._instances[service_name] = instance
        self.logger.info(f"Registered service instance: {service_name}")
    
    async def initialize_all_services(self) -> Dict[str, Any]:
        """Initialize all services and return summary"""
        self.logger.info("Initializing all services...")
        
        # Initialize services in dependency order
        services_created = []
        
        try:
            # Infrastructure services
            standardizer = self.get_standardizer_service()
            services_created.append('standardizer_service')
            
            cache = self.get_cache_service()
            if cache:
                services_created.append('cache_service')
            
            validator = self.get_validator_service()
            services_created.append('validator_service')
            
            # Provider services
            orchestrator = self.get_provider_orchestrator()
            services_created.append('provider_orchestrator')
            
            # Monitoring services
            health_monitor = self.get_health_monitor()
            services_created.append('health_monitor')
            
            resiliency = self.get_resiliency_manager()
            services_created.append('resiliency_manager')
            
            # Main services
            request_manager = self.get_request_manager()
            services_created.append('request_manager')
            
            translation_manager = self.get_translation_manager()
            services_created.append('translation_manager')
            
            # Set up health monitoring
            self.setup_health_monitoring()
            
            self.logger.info(f"Successfully initialized {len(services_created)} services")
            
            return {
                'success': True,
                'services_created': services_created,
                'total_services': len(services_created),
                'providers_available': len(orchestrator.get_available_providers()),
                'cache_enabled': cache is not None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            return {
                'success': False,
                'error': str(e),
                'services_created': services_created
            }
