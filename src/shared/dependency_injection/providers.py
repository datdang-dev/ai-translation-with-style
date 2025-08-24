"""
Service providers for advanced dependency injection scenarios.

These providers offer more sophisticated registration patterns
including conditional registration, configuration-based setup, and lifecycle management.
"""

from typing import Type, TypeVar, Callable, Dict, Any, Optional, List
from abc import ABC, abstractmethod

from .container import Container, Scope
from ..exceptions import ConfigurationException


T = TypeVar('T')


class IServiceProvider(ABC):
    """Interface for service providers."""
    
    @abstractmethod
    def register_services(self, container: Container) -> None:
        """Register services in the container."""
        pass


class ServiceProvider(IServiceProvider):
    """
    Base service provider class that enables modular service registration.
    
    Supports conditional registration, dependency ordering, and configuration-based setup.
    """
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self._registrations: List[Callable[[Container], None]] = []
        self._dependencies: List[Type['ServiceProvider']] = []
        self._conditions: List[Callable[[], bool]] = []
    
    def add_singleton(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None
    ) -> 'ServiceProvider':
        """Add a singleton registration."""
        def register(container: Container):
            container.register_singleton(service_type, implementation_type, factory, instance)
        
        self._registrations.append(register)
        return self
    
    def add_transient(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> 'ServiceProvider':
        """Add a transient registration."""
        def register(container: Container):
            container.register_transient(service_type, implementation_type, factory)
        
        self._registrations.append(register)
        return self
    
    def add_scoped(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> 'ServiceProvider':
        """Add a scoped registration."""
        def register(container: Container):
            container.register(service_type, implementation_type, factory, scope=Scope.SCOPED)
        
        self._registrations.append(register)
        return self
    
    def depends_on(self, provider_type: Type['ServiceProvider']) -> 'ServiceProvider':
        """Add a dependency on another service provider."""
        self._dependencies.append(provider_type)
        return self
    
    def when(self, condition: Callable[[], bool]) -> 'ServiceProvider':
        """Add a condition for registration."""
        self._conditions.append(condition)
        return self
    
    def register_services(self, container: Container) -> None:
        """Register all services if conditions are met."""
        # Check all conditions
        if not all(condition() for condition in self._conditions):
            return
        
        # Execute all registrations
        for registration in self._registrations:
            registration(container)
    
    def get_dependencies(self) -> List[Type['ServiceProvider']]:
        """Get provider dependencies."""
        return self._dependencies.copy()


class FactoryProvider(ServiceProvider):
    """
    Provider that specializes in factory-based service registration.
    
    Useful for services that require complex initialization or runtime configuration.
    """
    
    def __init__(self, name: str = None):
        super().__init__(name)
        self._factories: Dict[Type, Callable] = {}
    
    def add_factory(
        self,
        service_type: Type[T],
        factory: Callable[[], T],
        scope: Scope = Scope.TRANSIENT
    ) -> 'FactoryProvider':
        """Add a factory for a service type."""
        self._factories[service_type] = factory
        
        def register(container: Container):
            container.register(service_type, factory=factory, scope=scope)
        
        self._registrations.append(register)
        return self
    
    def add_conditional_factory(
        self,
        service_type: Type[T],
        factories: Dict[str, Callable[[], T]],
        condition_selector: Callable[[], str],
        scope: Scope = Scope.TRANSIENT
    ) -> 'FactoryProvider':
        """Add conditional factory selection based on runtime conditions."""
        def factory():
            selected_key = condition_selector()
            if selected_key not in factories:
                raise ConfigurationException(
                    f"No factory found for condition '{selected_key}' for service {service_type.__name__}",
                    error_code="FACTORY_NOT_FOUND"
                )
            return factories[selected_key]()
        
        return self.add_factory(service_type, factory, scope)


class InstanceProvider(ServiceProvider):
    """
    Provider for pre-created instances.
    
    Useful for sharing expensive resources or external service connections.
    """
    
    def __init__(self, name: str = None):
        super().__init__(name)
        self._instances: Dict[Type, Any] = {}
    
    def add_instance(self, service_type: Type[T], instance: T) -> 'InstanceProvider':
        """Add a pre-created instance."""
        self._instances[service_type] = instance
        
        def register(container: Container):
            container.register_singleton(service_type, instance=instance)
        
        self._registrations.append(register)
        return self
    
    def get_instance(self, service_type: Type[T]) -> Optional[T]:
        """Get a registered instance."""
        return self._instances.get(service_type)


class ConfigurationBasedProvider(ServiceProvider):
    """
    Provider that registers services based on configuration.
    
    Enables dynamic service registration based on application configuration.
    """
    
    def __init__(self, config: Dict[str, Any], name: str = None):
        super().__init__(name)
        self.config = config
    
    def register_from_config(
        self,
        config_key: str,
        service_type: Type[T],
        implementation_mapping: Dict[str, Type[T]],
        default_scope: Scope = Scope.TRANSIENT
    ) -> 'ConfigurationBasedProvider':
        """Register a service based on configuration value."""
        def register(container: Container):
            config_value = self.config.get(config_key)
            if config_value is None:
                return
            
            if config_value not in implementation_mapping:
                raise ConfigurationException(
                    f"No implementation found for config value '{config_value}' for service {service_type.__name__}",
                    error_code="IMPLEMENTATION_NOT_FOUND",
                    context={"config_key": config_key, "config_value": config_value}
                )
            
            implementation_type = implementation_mapping[config_value]
            container.register(service_type, implementation_type, scope=default_scope)
        
        self._registrations.append(register)
        return self


class ConditionalProvider(ServiceProvider):
    """
    Provider that enables conditional service registration.
    
    Useful for environment-specific or feature-flag-based service registration.
    """
    
    def __init__(self, name: str = None):
        super().__init__(name)
    
    def register_if(
        self,
        condition: Callable[[], bool],
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None,
        scope: Scope = Scope.TRANSIENT
    ) -> 'ConditionalProvider':
        """Register a service only if condition is met."""
        def register(container: Container):
            if condition():
                container.register(service_type, implementation_type, factory, instance, scope)
        
        self._registrations.append(register)
        return self
    
    def register_environment_specific(
        self,
        environment: str,
        current_environment: str,
        service_type: Type[T],
        implementation_type: Type[T],
        scope: Scope = Scope.TRANSIENT
    ) -> 'ConditionalProvider':
        """Register a service for a specific environment."""
        return self.register_if(
            lambda: current_environment == environment,
            service_type,
            implementation_type,
            scope=scope
        )


class ServiceProviderRegistry:
    """
    Registry for managing and executing service providers in dependency order.
    """
    
    def __init__(self):
        self._providers: Dict[Type[ServiceProvider], ServiceProvider] = {}
        self._execution_order: List[ServiceProvider] = []
    
    def add_provider(self, provider: ServiceProvider) -> None:
        """Add a service provider to the registry."""
        provider_type = type(provider)
        self._providers[provider_type] = provider
        self._calculate_execution_order()
    
    def register_all(self, container: Container) -> None:
        """Register all services from all providers in dependency order."""
        for provider in self._execution_order:
            provider.register_services(container)
    
    def _calculate_execution_order(self) -> None:
        """Calculate the execution order based on dependencies."""
        # Simple topological sort
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(provider: ServiceProvider):
            if provider in temp_visited:
                raise ConfigurationException(
                    f"Circular dependency detected in service providers",
                    error_code="CIRCULAR_PROVIDER_DEPENDENCY"
                )
            
            if provider in visited:
                return
            
            temp_visited.add(provider)
            
            for dep_type in provider.get_dependencies():
                if dep_type in self._providers:
                    visit(self._providers[dep_type])
            
            temp_visited.remove(provider)
            visited.add(provider)
            result.append(provider)
        
        for provider in self._providers.values():
            if provider not in visited:
                visit(provider)
        
        self._execution_order = result