"""
Server fault handler for managing provider failures and recovery
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from services.models import ProviderError, HealthStatus
from services.common.logger import get_logger


class FaultType(Enum):
    """Types of faults that can occur"""
    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"
    NETWORK_ERROR = "network_error"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class RetryPolicy:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True


@dataclass
class CircuitBreakerState:
    """State of a circuit breaker"""
    failure_count: int = 0
    last_failure_time: float = 0
    state: str = "closed"  # closed, open, half_open
    last_success_time: float = 0
    consecutive_successes: int = 0


class ServerFaultHandler:
    """Handles server faults with retry, circuit breaker, and fallback logic"""
    
    def __init__(self, 
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 circuit_breaker_threshold: int = 5,
                 circuit_breaker_timeout: float = 60.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        
        self.logger = get_logger("ServerFaultHandler")
        
        # Circuit breaker states per provider
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        
        # Retry policies per provider
        self.retry_policies: Dict[str, RetryPolicy] = {}
        
        # Default retry policy
        self.default_retry_policy = RetryPolicy(
            max_attempts=max_retries,
            base_delay=retry_delay
        )
        
        # Fault statistics
        self.fault_stats: Dict[str, Dict[str, int]] = {}
    
    def set_retry_policy(self, provider: str, policy: RetryPolicy):
        """Set retry policy for a specific provider"""
        self.retry_policies[provider] = policy
        self.logger.info(f"Set retry policy for {provider}: max_attempts={policy.max_attempts}")
    
    def get_retry_policy(self, provider: str) -> RetryPolicy:
        """Get retry policy for provider"""
        return self.retry_policies.get(provider, self.default_retry_policy)
    
    def _get_circuit_breaker(self, provider: str) -> CircuitBreakerState:
        """Get or create circuit breaker state for provider"""
        if provider not in self.circuit_breakers:
            self.circuit_breakers[provider] = CircuitBreakerState()
        return self.circuit_breakers[provider]
    
    def _record_fault(self, provider: str, fault_type: FaultType):
        """Record a fault for statistics"""
        if provider not in self.fault_stats:
            self.fault_stats[provider] = {}
        
        fault_key = fault_type.value
        self.fault_stats[provider][fault_key] = self.fault_stats[provider].get(fault_key, 0) + 1
    
    async def execute_with_retry(self, 
                               func: Callable,
                               provider: str = "default",
                               *args, 
                               **kwargs) -> Any:
        """Execute function with retry logic and circuit breaker"""
        circuit_breaker = self._get_circuit_breaker(provider)
        
        # Check circuit breaker state
        if not self._is_circuit_closed(circuit_breaker, provider):
            raise ProviderError(f"Circuit breaker open for {provider}", error_code="CIRCUIT_OPEN")
        
        retry_policy = self.get_retry_policy(provider)
        last_exception = None
        
        for attempt in range(retry_policy.max_attempts):
            try:
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Success - record it
                self._record_success(circuit_breaker, provider)
                return result
                
            except Exception as e:
                last_exception = e
                fault_type = self._classify_fault(e)
                
                self.logger.warning(
                    f"Attempt {attempt + 1}/{retry_policy.max_attempts} failed "
                    f"for {provider}: {fault_type.value} - {e}"
                )
                
                # Record fault
                self._record_fault(provider, fault_type)
                self._record_failure(circuit_breaker, provider)
                
                # Check if we should retry
                if not self._should_retry(fault_type, attempt + 1, retry_policy.max_attempts):
                    break
                
                # Calculate delay for next attempt
                if attempt < retry_policy.max_attempts - 1:
                    delay = self._calculate_delay(attempt, retry_policy)
                    self.logger.info(f"Retrying {provider} in {delay:.2f} seconds")
                    await asyncio.sleep(delay)
        
        # All retries failed
        self.logger.error(f"All {retry_policy.max_attempts} attempts failed for {provider}")
        
        if last_exception:
            raise last_exception
        else:
            raise ProviderError(f"All retry attempts failed for {provider}")
    
    def _classify_fault(self, exception: Exception) -> FaultType:
        """Classify exception into fault type"""
        if isinstance(exception, ProviderError):
            error_code = getattr(exception, 'error_code', 'UNKNOWN')
            
            if error_code == "RATE_LIMIT":
                return FaultType.RATE_LIMIT
            elif error_code == "AUTH_ERROR":
                return FaultType.AUTH_ERROR
            elif error_code == "NETWORK_ERROR":
                return FaultType.NETWORK_ERROR
            elif error_code == "SERVER_ERROR":
                return FaultType.SERVER_ERROR
            elif error_code == "TIMEOUT":
                return FaultType.TIMEOUT
        
        # Check exception type/message for classification
        error_str = str(exception).lower()
        
        if "timeout" in error_str or "timed out" in error_str:
            return FaultType.TIMEOUT
        elif "rate limit" in error_str or "429" in error_str:
            return FaultType.RATE_LIMIT
        elif "unauthorized" in error_str or "401" in error_str or "403" in error_str:
            return FaultType.AUTH_ERROR
        elif "network" in error_str or "connection" in error_str:
            return FaultType.NETWORK_ERROR
        elif "server" in error_str or any(code in error_str for code in ["500", "502", "503", "504"]):
            return FaultType.SERVER_ERROR
        
        return FaultType.UNKNOWN
    
    def _should_retry(self, fault_type: FaultType, attempt: int, max_attempts: int) -> bool:
        """Determine if we should retry based on fault type"""
        if attempt >= max_attempts:
            return False
        
        # Don't retry auth errors
        if fault_type == FaultType.AUTH_ERROR:
            return False
        
        # Retry other types of errors
        return True
    
    def _calculate_delay(self, attempt: int, policy: RetryPolicy) -> float:
        """Calculate delay for retry with exponential backoff"""
        delay = policy.base_delay * (policy.backoff_multiplier ** attempt)
        delay = min(delay, policy.max_delay)
        
        # Add jitter to prevent thundering herd
        if policy.jitter:
            import random
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def _is_circuit_closed(self, circuit_breaker: CircuitBreakerState, provider: str) -> bool:
        """Check if circuit breaker allows requests"""
        current_time = time.time()
        
        if circuit_breaker.state == "closed":
            return True
        elif circuit_breaker.state == "open":
            # Check if timeout has passed
            if current_time - circuit_breaker.last_failure_time >= self.circuit_breaker_timeout:
                circuit_breaker.state = "half_open"
                circuit_breaker.consecutive_successes = 0
                self.logger.info(f"Circuit breaker for {provider} moved to half-open")
                return True
            return False
        elif circuit_breaker.state == "half_open":
            return True
        
        return False
    
    def _record_success(self, circuit_breaker: CircuitBreakerState, provider: str):
        """Record successful operation"""
        current_time = time.time()
        circuit_breaker.last_success_time = current_time
        
        if circuit_breaker.state == "half_open":
            circuit_breaker.consecutive_successes += 1
            
            # Close circuit after successful attempts
            if circuit_breaker.consecutive_successes >= 2:
                circuit_breaker.state = "closed"
                circuit_breaker.failure_count = 0
                self.logger.info(f"Circuit breaker for {provider} closed after successful recovery")
        elif circuit_breaker.state == "closed":
            # Reset failure count on success
            circuit_breaker.failure_count = max(0, circuit_breaker.failure_count - 1)
    
    def _record_failure(self, circuit_breaker: CircuitBreakerState, provider: str):
        """Record failed operation"""
        current_time = time.time()
        circuit_breaker.last_failure_time = current_time
        circuit_breaker.failure_count += 1
        
        # Open circuit if threshold exceeded
        if circuit_breaker.failure_count >= self.circuit_breaker_threshold:
            if circuit_breaker.state != "open":
                circuit_breaker.state = "open"
                self.logger.warning(
                    f"Circuit breaker for {provider} opened after "
                    f"{circuit_breaker.failure_count} failures"
                )
    
    def handle_rate_limit(self, provider: str = "default") -> bool:
        """Handle rate limit specifically"""
        circuit_breaker = self._get_circuit_breaker(provider)
        self._record_fault(provider, FaultType.RATE_LIMIT)
        
        # For rate limits, we might want different behavior
        # For now, just record the failure
        self._record_failure(circuit_breaker, provider)
        
        self.logger.warning(f"Rate limit encountered for {provider}")
        return True
    
    def handle_retry(self, attempt: int, provider: str = "default") -> bool:
        """Handle retry decision"""
        retry_policy = self.get_retry_policy(provider)
        
        if attempt >= retry_policy.max_attempts:
            return False
        
        self.logger.info(f"Retry attempt {attempt} for {provider}")
        return True
    
    def handle_fallback(self, failed_provider: str) -> Optional[str]:
        """Handle fallback provider selection"""
        # This is a simple implementation
        # In practice, this would integrate with ProviderOrchestrator
        
        fallback_providers = ["google_translate", "openrouter"]
        
        for provider in fallback_providers:
            if provider != failed_provider:
                circuit_breaker = self._get_circuit_breaker(provider)
                if self._is_circuit_closed(circuit_breaker, provider):
                    self.logger.info(f"Falling back from {failed_provider} to {provider}")
                    return provider
        
        self.logger.warning(f"No fallback available for {failed_provider}")
        return None
    
    def get_circuit_breaker_status(self, provider: str) -> Dict[str, Any]:
        """Get circuit breaker status for provider"""
        circuit_breaker = self._get_circuit_breaker(provider)
        
        return {
            'provider': provider,
            'state': circuit_breaker.state,
            'failure_count': circuit_breaker.failure_count,
            'last_failure_time': circuit_breaker.last_failure_time,
            'last_success_time': circuit_breaker.last_success_time,
            'consecutive_successes': circuit_breaker.consecutive_successes,
            'threshold': self.circuit_breaker_threshold,
            'timeout': self.circuit_breaker_timeout
        }
    
    def get_fault_statistics(self) -> Dict[str, Any]:
        """Get fault statistics for all providers"""
        return {
            'providers': dict(self.fault_stats),
            'circuit_breakers': {
                provider: self.get_circuit_breaker_status(provider)
                for provider in self.circuit_breakers
            },
            'retry_policies': {
                provider: {
                    'max_attempts': policy.max_attempts,
                    'base_delay': policy.base_delay,
                    'backoff_multiplier': policy.backoff_multiplier
                }
                for provider, policy in self.retry_policies.items()
            }
        }
    
    def reset_circuit_breaker(self, provider: str):
        """Manually reset circuit breaker for provider"""
        if provider in self.circuit_breakers:
            self.circuit_breakers[provider] = CircuitBreakerState()
            self.logger.info(f"Circuit breaker reset for {provider}")
    
    def reset_fault_stats(self, provider: str = None):
        """Reset fault statistics"""
        if provider:
            self.fault_stats.pop(provider, None)
            self.logger.info(f"Fault statistics reset for {provider}")
        else:
            self.fault_stats.clear()
            self.logger.info("All fault statistics reset")