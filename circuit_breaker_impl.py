"""
Circuit breaker pattern implementation for API resilience.
"""

import time
import asyncio
from typing import Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass

from ..core.interfaces import IConfigurationService, Result
from ..core.exceptions import CircuitBreakerError


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, calls rejected
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5      # Failures before opening
    recovery_timeout: float = 60.0  # Seconds before trying half-open
    success_threshold: int = 2      # Successes needed to close from half-open
    timeout: float = 30.0           # Request timeout


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.last_success_time = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Result:
        """Execute function with circuit breaker protection"""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    return Result.error(503, f"Circuit breaker {self.name} is OPEN")
            
            if self.state == CircuitState.HALF_OPEN:
                if self.success_count >= self.config.success_threshold:
                    self._reset()
        
        # Execute the function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs), 
                    timeout=self.config.timeout
                )
            else:
                result = func(*args, **kwargs)
            
            await self._on_success()
            
            # If result is a Result object, return it; otherwise wrap it
            if isinstance(result, Result):
                return result
            else:
                return Result.ok(result)
                
        except asyncio.TimeoutError:
            await self._on_failure("Request timeout")
            return Result.error(408, f"Circuit breaker {self.name}: Request timeout")
        except Exception as e:
            await self._on_failure(str(e))
            return Result.error(500, f"Circuit breaker {self.name}: {str(e)}")
    
    async def _on_success(self) -> None:
        """Handle successful call"""
        async with self._lock:
            self.last_success_time = time.time()
            self.failure_count = 0
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self._reset()
    
    async def _on_failure(self, error: str) -> None:
        """Handle failed call"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                self.success_count = 0
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset to half-open"""
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout
    
    def _reset(self) -> None:
        """Reset circuit to closed state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
    
    async def get_status(self) -> dict:
        """Get circuit breaker status"""
        async with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time,
                "last_success_time": self.last_success_time,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "success_threshold": self.config.success_threshold,
                    "timeout": self.config.timeout
                }
            }
    
    async def force_open(self) -> None:
        """Force circuit to open state (for testing/emergency)"""
        async with self._lock:
            self.state = CircuitState.OPEN
            self.last_failure_time = time.time()
    
    async def force_close(self) -> None:
        """Force circuit to closed state (for recovery)"""
        async with self._lock:
            self._reset()


class CircuitBreakerManager:
    """Manages multiple circuit breakers"""
    
    def __init__(self, config_service: IConfigurationService):
        self.config_service = config_service
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    async def get_breaker(self, name: str) -> CircuitBreaker:
        """Get or create circuit breaker"""
        async with self._lock:
            if name not in self._breakers:
                # Load config for this breaker
                breaker_config = CircuitBreakerConfig(
                    failure_threshold=self.config_service.get(f"circuit_breaker.{name}.failure_threshold", 5),
                    recovery_timeout=self.config_service.get(f"circuit_breaker.{name}.recovery_timeout", 60.0),
                    success_threshold=self.config_service.get(f"circuit_breaker.{name}.success_threshold", 2),
                    timeout=self.config_service.get(f"circuit_breaker.{name}.timeout", 30.0)
                )
                self._breakers[name] = CircuitBreaker(name, breaker_config)
            
            return self._breakers[name]
    
    async def call_with_breaker(self, breaker_name: str, func: Callable, *args, **kwargs) -> Result:
        """Execute function with named circuit breaker"""
        breaker = await self.get_breaker(breaker_name)
        return await breaker.call(func, *args, **kwargs)
    
    async def get_all_statuses(self) -> dict:
        """Get status of all circuit breakers"""
        async with self._lock:
            statuses = {}
            for name, breaker in self._breakers.items():
                statuses[name] = await breaker.get_status()
            return statuses