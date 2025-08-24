"""
Dependency Injection Container

Provides inversion of control for the translation framework,
enabling testable, modular, and configurable component management.
"""

from .container import Container, Scope
from .decorators import inject, singleton, transient
from .providers import ServiceProvider, FactoryProvider, InstanceProvider

__all__ = [
    "Container",
    "Scope", 
    "inject",
    "singleton",
    "transient",
    "ServiceProvider",
    "FactoryProvider", 
    "InstanceProvider"
]