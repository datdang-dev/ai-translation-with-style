"""
Core interfaces for the translation service architecture.
These interfaces define contracts for loose coupling and better testability.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass


class ServiceStatus(Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthStatus:
    """Health check result"""
    status: ServiceStatus
    message: str
    details: Dict[str, Any] = None
    timestamp: float = None


@dataclass
class Result:
    """Result pattern for better error handling"""
    success: bool
    data: Any = None
    error_code: int = 0
    error_message: str = ""
    
    @classmethod
    def ok(cls, data: Any = None):
        return cls(success=True, data=data)
    
    @classmethod
    def error(cls, error_code: int, message: str):
        return cls(success=False, error_code=error_code, error_message=message)


class IConfigurationService(ABC):
    """Interface for configuration management"""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        pass
    
    @abstractmethod
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get configuration section"""
        pass
    
    @abstractmethod
    def reload(self) -> Result:
        """Reload configuration"""
        pass


class IAPIKeyManager(ABC):
    """Interface for API key management"""
    
    @abstractmethod
    async def get_next_available_key(self) -> Optional[Dict[str, Any]]:
        """Get next available API key"""
        pass
    
    @abstractmethod
    async def mark_key_status(self, key_name: str, status: str) -> None:
        """Mark key status"""
        pass


class IAPIClient(ABC):
    """Interface for API clients"""
    
    @abstractmethod
    async def send_request(self, data: Dict[str, Any]) -> Result:
        """Send API request"""
        pass


class IMetricsService(ABC):
    """Interface for metrics collection"""
    
    @abstractmethod
    def increment_counter(self, name: str, tags: Dict[str, str] = None) -> None:
        """Increment counter metric"""
        pass
    
    @abstractmethod
    def record_duration(self, name: str, duration: float, tags: Dict[str, str] = None) -> None:
        """Record duration metric"""
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        pass


class IHealthCheck(ABC):
    """Interface for health checks"""
    
    @abstractmethod
    async def check_health(self) -> HealthStatus:
        """Check service health"""
        pass


class IRequestHandler(ABC):
    """Interface for request handling"""
    
    @abstractmethod
    async def handle_request(self, data: Dict[str, Any]) -> Result:
        """Handle translation request"""
        pass


class IJobQueue(ABC):
    """Interface for job queue management"""
    
    @abstractmethod
    async def enqueue(self, job: Any, priority: int = 0) -> str:
        """Enqueue job"""
        pass
    
    @abstractmethod
    async def dequeue(self) -> Optional[Any]:
        """Dequeue job"""
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get queue status"""
        pass