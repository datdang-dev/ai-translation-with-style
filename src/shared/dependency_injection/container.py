"""
Dependency Injection Container Implementation

A lightweight, type-safe dependency injection container that supports
scoped lifecycles, circular dependency detection, and configuration-based registration.
"""

from typing import TypeVar, Type, Dict, Any, Optional, Callable, Union, get_type_hints
from enum import Enum
import inspect
import threading
from contextlib import contextmanager

from ..exceptions import ConfigurationException


T = TypeVar('T')


class Scope(Enum):
    """Service lifecycle scopes."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class ServiceRegistration:
    """Represents a service registration in the container."""
    
    def __init__(
        self,
        service_type: Type,
        implementation_type: Optional[Type] = None,
        factory: Optional[Callable] = None,
        instance: Optional[Any] = None,
        scope: Scope = Scope.TRANSIENT
    ):
        self.service_type = service_type
        self.implementation_type = implementation_type
        self.factory = factory
        self.instance = instance
        self.scope = scope
        
        # Validation
        if sum(bool(x) for x in [implementation_type, factory, instance]) != 1:
            raise ConfigurationException(
                "Exactly one of implementation_type, factory, or instance must be provided"
            )


class Container:
    """
    Dependency injection container with support for type-safe service registration
    and resolution with lifecycle management.
    """
    
    def __init__(self):
        self._services: Dict[Type, ServiceRegistration] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_instances: Dict[Type, Any] = {}
        self._resolution_stack: list = []
        self._lock = threading.RLock()
    
    def register(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None,
        scope: Scope = Scope.TRANSIENT
    ) -> 'Container':
        """
        Register a service in the container.
        
        Args:
            service_type: The interface or abstract type to register
            implementation_type: Concrete implementation class
            factory: Factory function to create instances
            instance: Pre-created instance (for singleton registration)
            scope: Service lifecycle scope
            
        Returns:
            Self for fluent configuration
        """
        with self._lock:
            registration = ServiceRegistration(
                service_type=service_type,
                implementation_type=implementation_type,
                factory=factory,
                instance=instance,
                scope=scope
            )
            
            self._services[service_type] = registration
            
            # For singleton instances, store immediately
            if instance is not None and scope == Scope.SINGLETON:
                self._singletons[service_type] = instance
            
            return self
    
    def register_singleton(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None
    ) -> 'Container':
        """Register a service as singleton."""
        return self.register(service_type, implementation_type, factory, instance, Scope.SINGLETON)
    
    def register_transient(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> 'Container':
        """Register a service as transient."""
        return self.register(service_type, implementation_type, factory, None, Scope.TRANSIENT)
    
    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service instance from the container.
        
        Args:
            service_type: The type to resolve
            
        Returns:
            Service instance
            
        Raises:
            ConfigurationException: If service is not registered or circular dependency detected
        """
        with self._lock:
            return self._resolve_internal(service_type)
    
    def _resolve_internal(self, service_type: Type[T]) -> T:
        """Internal resolution method with circular dependency detection."""
        # Check for circular dependencies
        if service_type in self._resolution_stack:
            cycle = " -> ".join([t.__name__ for t in self._resolution_stack] + [service_type.__name__])
            raise ConfigurationException(
                f"Circular dependency detected: {cycle}",
                error_code="CIRCULAR_DEPENDENCY"
            )
        
        # Check if service is registered
        if service_type not in self._services:
            raise ConfigurationException(
                f"Service {service_type.__name__} is not registered",
                error_code="SERVICE_NOT_REGISTERED"
            )
        
        registration = self._services[service_type]
        
        # Handle singleton scope
        if registration.scope == Scope.SINGLETON:
            if service_type in self._singletons:
                return self._singletons[service_type]
        
        # Handle scoped instances
        elif registration.scope == Scope.SCOPED:
            if service_type in self._scoped_instances:
                return self._scoped_instances[service_type]
        
        # Create new instance
        self._resolution_stack.append(service_type)
        try:
            instance = self._create_instance(registration)
            
            # Store based on scope
            if registration.scope == Scope.SINGLETON:
                self._singletons[service_type] = instance
            elif registration.scope == Scope.SCOPED:
                self._scoped_instances[service_type] = instance
            
            return instance
        finally:
            self._resolution_stack.pop()
    
    def _create_instance(self, registration: ServiceRegistration) -> Any:
        """Create a new instance based on registration type."""
        if registration.instance is not None:
            return registration.instance
        
        if registration.factory is not None:
            return self._invoke_with_injection(registration.factory)
        
        if registration.implementation_type is not None:
            return self._create_instance_from_type(registration.implementation_type)
        
        raise ConfigurationException(
            "Invalid registration: no way to create instance",
            error_code="INVALID_REGISTRATION"
        )
    
    def _create_instance_from_type(self, implementation_type: Type) -> Any:
        """Create instance from type with constructor injection."""
        constructor = implementation_type.__init__
        return self._invoke_with_injection(implementation_type)
    
    def _invoke_with_injection(self, callable_obj: Callable) -> Any:
        """Invoke a callable with dependency injection."""
        # Get type hints for parameters
        if inspect.isclass(callable_obj):
            # For class constructors
            signature = inspect.signature(callable_obj.__init__)
            type_hints = get_type_hints(callable_obj.__init__)
            skip_self = True
        else:
            # For regular functions
            signature = inspect.signature(callable_obj)
            type_hints = get_type_hints(callable_obj)
            skip_self = False
        
        kwargs = {}
        for param_name, param in signature.parameters.items():
            if skip_self and param_name == 'self':
                continue
            
            # Skip parameters with default values if type hint not available
            if param_name not in type_hints:
                if param.default != inspect.Parameter.empty:
                    continue
                else:
                    raise ConfigurationException(
                        f"Cannot resolve parameter '{param_name}' for {callable_obj}: no type hint provided",
                        error_code="MISSING_TYPE_HINT"
                    )
            
            param_type = type_hints[param_name]
            
            # Skip optional parameters that aren't registered
            if param.default != inspect.Parameter.empty and param_type not in self._services:
                continue
            
            kwargs[param_name] = self._resolve_internal(param_type)
        
        if inspect.isclass(callable_obj):
            return callable_obj(**kwargs)
        else:
            return callable_obj(**kwargs)
    
    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._services
    
    def clear_scoped(self) -> None:
        """Clear all scoped instances."""
        with self._lock:
            self._scoped_instances.clear()
    
    @contextmanager
    def scope(self):
        """Create a new scope context."""
        try:
            yield self
        finally:
            self.clear_scoped()
    
    def create_child_container(self) -> 'Container':
        """Create a child container that inherits parent registrations."""
        child = Container()
        child._services.update(self._services)
        child._singletons.update(self._singletons)
        return child
    
    def get_registrations(self) -> Dict[Type, ServiceRegistration]:
        """Get all service registrations (for debugging/testing)."""
        return self._services.copy()


# Global container instance
_global_container = Container()


def get_container() -> Container:
    """Get the global container instance."""
    return _global_container


def set_container(container: Container) -> None:
    """Set the global container instance."""
    global _global_container
    _global_container = container