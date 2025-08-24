"""
Dependency injection decorators for easy service registration and injection.
"""

from typing import TypeVar, Type, Callable, Any
import functools

from .container import get_container, Scope


T = TypeVar('T')


def inject(service_type: Type[T]) -> Callable[[Callable], Callable]:
    """
    Decorator to inject a service into a function parameter.
    
    Usage:
        @inject(ILogger)
        def my_function(logger: ILogger):
            logger.info("Hello")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            container = get_container()
            if 'logger' not in kwargs:  # Example - this would need more sophisticated parameter mapping
                kwargs['logger'] = container.resolve(service_type)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def singleton(service_type: Type[T] = None) -> Callable:
    """
    Decorator to register a class as a singleton service.
    
    Usage:
        @singleton(IMyService)
        class MyService(IMyService):
            pass
    """
    def decorator(cls: Type[T]) -> Type[T]:
        container = get_container()
        target_type = service_type if service_type is not None else cls
        container.register_singleton(target_type, implementation_type=cls)
        return cls
    
    if service_type is None:
        # Used as @singleton without parentheses
        return decorator
    else:
        # Used as @singleton(IMyService) with parentheses
        return decorator


def transient(service_type: Type[T] = None) -> Callable:
    """
    Decorator to register a class as a transient service.
    
    Usage:
        @transient(IMyService)
        class MyService(IMyService):
            pass
    """
    def decorator(cls: Type[T]) -> Type[T]:
        container = get_container()
        target_type = service_type if service_type is not None else cls
        container.register_transient(target_type, implementation_type=cls)
        return cls
    
    if service_type is None:
        # Used as @transient without parentheses
        return decorator
    else:
        # Used as @transient(IMyService) with parentheses
        return decorator


def scoped(service_type: Type[T] = None) -> Callable:
    """
    Decorator to register a class as a scoped service.
    
    Usage:
        @scoped(IMyService)
        class MyService(IMyService):
            pass
    """
    def decorator(cls: Type[T]) -> Type[T]:
        container = get_container()
        target_type = service_type if service_type is not None else cls
        container.register(target_type, implementation_type=cls, scope=Scope.SCOPED)
        return cls
    
    if service_type is None:
        # Used as @scoped without parentheses
        return decorator
    else:
        # Used as @scoped(IMyService) with parentheses
        return decorator


def factory(service_type: Type[T], scope: Scope = Scope.TRANSIENT) -> Callable:
    """
    Decorator to register a function as a factory for a service.
    
    Usage:
        @factory(IMyService, Scope.SINGLETON)
        def create_my_service() -> IMyService:
            return MyService()
    """
    def decorator(func: Callable[[], T]) -> Callable[[], T]:
        container = get_container()
        container.register(service_type, factory=func, scope=scope)
        return func
    
    return decorator


class Injected:
    """
    Marker class for dependency injection in function parameters.
    
    Usage:
        def my_function(logger: ILogger = Injected(ILogger)):
            logger.info("Hello")
    """
    
    def __init__(self, service_type: Type[T]):
        self.service_type = service_type
    
    def __repr__(self):
        return f"Injected({self.service_type.__name__})"


def auto_inject(func: Callable) -> Callable:
    """
    Decorator that automatically injects dependencies marked with Injected().
    
    Usage:
        @auto_inject
        def my_function(logger: ILogger = Injected(ILogger)):
            logger.info("Hello")
    """
    import inspect
    
    signature = inspect.signature(func)
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        container = get_container()
        
        # Get bound arguments
        bound_args = signature.bind_partial(*args, **kwargs)
        
        # Inject missing dependencies
        for param_name, param in signature.parameters.items():
            if param_name not in bound_args.arguments and isinstance(param.default, Injected):
                bound_args.arguments[param_name] = container.resolve(param.default.service_type)
        
        return func(*bound_args.args, **bound_args.kwargs)
    
    return wrapper