"""Health check interface"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class HealthStatus(str, Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    checked_at: datetime
    response_time_ms: Optional[int] = None
    
    @property
    def is_healthy(self) -> bool:
        """Check if the service is healthy"""
        return self.status == HealthStatus.HEALTHY
    
    @property
    def is_available(self) -> bool:
        """Check if the service is available (healthy or degraded)"""
        return self.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]


class HealthCheck(ABC):
    """
    Abstract interface for health checks.
    
    Provides a standard way to check the health of various components
    like providers, databases, external services, etc.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the name of this health check.
        
        Returns:
            Human-readable name for the health check
        """
        pass
    
    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """
        Perform the health check.
        
        Should be lightweight and fast (typically < 5 seconds).
        
        Returns:
            HealthCheckResult with status and details
        """
        pass
    
    async def is_healthy(self) -> bool:
        """
        Quick check if the component is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            result = await self.check()
            return result.is_healthy
        except Exception:
            return False
    
    async def is_available(self) -> bool:
        """
        Quick check if the component is available.
        
        Returns:
            True if available (healthy or degraded), False otherwise
        """
        try:
            result = await self.check()
            return result.is_available
        except Exception:
            return False