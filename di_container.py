"""
Dependency injection container for better testability and loose coupling.
"""

from typing import Dict, Any, Callable, Optional, TypeVar, Type
from functools import wraps
import inspect

from .interfaces import *
from .exceptions import ConfigurationError


T = TypeVar('T')


class DIContainer:
    """Simple dependency injection container"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._interfaces: Dict[Type, str] = {}
    
    def register_singleton(self, interface: Type[T], implementation: T, name: str = None) -> None:
        """Register a singleton service"""
        service_name = name or interface.__name__
        self._singletons[service_name] = implementation
        self._interfaces[interface] = service_name
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T], name: str = None) -> None:
        """Register a factory function for service creation"""
        service_name = name or interface.__name__
        self._factories[service_name] = factory
        self._interfaces[interface] = service_name
    
    def register_transient(self, interface: Type[T], implementation_class: Type[T], name: str = None) -> None:
        """Register a transient service (new instance each time)"""
        service_name = name or interface.__name__
        self._services[service_name] = implementation_class
        self._interfaces[interface] = service_name
    
    def get(self, interface: Type[T]) -> T:
        """Get service instance by interface"""
        service_name = self._interfaces.get(interface)
        if not service_name:
            raise ConfigurationError(f"Service not registered for interface: {interface}")
        
        return self._resolve(service_name)
    
    def get_by_name(self, name: str) -> Any:
        """Get service instance by name"""
        return self._resolve(name)
    
    def _resolve(self, name: str) -> Any:
        """Resolve service by name"""
        # Check singletons first
        if name in self._singletons:
            return self._singletons[name]
        
        # Check factories
        if name in self._factories:
            instance = self._factories[name]()
            return instance
        
        # Check transient services
        if name in self._services:
            service_class = self._services[name]
            # Auto-wire constructor dependencies
            return self._create_instance(service_class)
        
        raise ConfigurationError(f"Service not found: {name}")
    
    def _create_instance(self, service_class: Type) -> Any:
        """Create instance with dependency injection"""
        signature = inspect.signature(service_class.__init__)
        kwargs = {}
        
        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue
            
            if param.annotation != inspect.Parameter.empty:
                # Try to resolve by type annotation
                try:
                    kwargs[param_name] = self.get(param.annotation)
                except ConfigurationError:
                    # If no service registered for this type, skip if has default
                    if param.default == inspect.Parameter.empty:
                        raise ConfigurationError(
                            f"Cannot resolve dependency {param_name} of type {param.annotation} for {service_class}"
                        )
        
        return service_class(**kwargs)


# Global container instance
container = DIContainer()


def inject(interface: Type[T]) -> T:
    """Decorator for dependency injection"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Inject dependencies based on function signature
            signature = inspect.signature(func)
            injected_kwargs = {}
            
            for param_name, param in signature.parameters.items():
                if param.annotation != inspect.Parameter.empty and param_name not in kwargs:
                    try:
                        injected_kwargs[param_name] = container.get(param.annotation)
                    except ConfigurationError:
                        pass  # Skip if not registered
            
            return func(*args, **kwargs, **injected_kwargs)
        return wrapper
    return decorator