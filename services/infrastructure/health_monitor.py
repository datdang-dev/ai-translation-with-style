"""
Health monitoring service for tracking provider and service health
"""

import asyncio
import time
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass
from services.models import HealthStatus
from services.common.logger import get_logger


@dataclass
class HealthCheckConfig:
    """Configuration for health checks"""
    interval: float = 60.0  # Check interval in seconds
    timeout: float = 10.0   # Timeout for health check
    enabled: bool = True
    consecutive_failures_threshold: int = 3


class HealthMonitor:
    """Health monitoring service for providers and services"""
    
    def __init__(self):
        self.logger = get_logger("HealthMonitor")
        
        # Health check configurations
        self.check_configs: Dict[str, HealthCheckConfig] = {}
        
        # Health check functions
        self.health_checkers: Dict[str, Callable] = {}
        
        # Current health status
        self.health_status: Dict[str, HealthStatus] = {}
        
        # Statistics for each provider
        self.provider_stats: Dict[str, Dict[str, Any]] = {}
        
        # Monitoring control
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_enabled = False
        self._shutdown_event = asyncio.Event()
    
    def register_health_check(self, 
                            provider: str, 
                            health_checker: Callable,
                            config: HealthCheckConfig = None):
        """Register health check for a provider"""
        self.health_checkers[provider] = health_checker
        self.check_configs[provider] = config or HealthCheckConfig()
        
        # Initialize health status
        self.health_status[provider] = HealthStatus.healthy(f"{provider} registered")
        
        # Initialize stats
        self.provider_stats[provider] = {
            'total_checks': 0,
            'successful_checks': 0,
            'failed_checks': 0,
            'consecutive_failures': 0,
            'last_check_time': 0,
            'average_response_time': 0.0,
            'min_response_time': float('inf'),
            'max_response_time': 0.0
        }
        
        self.logger.info(f"Registered health check for {provider}")
    
    def unregister_health_check(self, provider: str):
        """Unregister health check for a provider"""
        self.health_checkers.pop(provider, None)
        self.check_configs.pop(provider, None)
        self.health_status.pop(provider, None)
        self.provider_stats.pop(provider, None)
        
        self.logger.info(f"Unregistered health check for {provider}")
    
    async def check_health(self, provider: str) -> HealthStatus:
        """Perform immediate health check for a provider"""
        if provider not in self.health_checkers:
            return HealthStatus.unhealthy(f"No health checker registered for {provider}")
        
        health_checker = self.health_checkers[provider]
        config = self.check_configs[provider]
        stats = self.provider_stats[provider]
        
        start_time = time.time()
        
        try:
            # Execute health check with timeout
            health = await asyncio.wait_for(
                health_checker(),
                timeout=config.timeout
            )
            
            response_time = time.time() - start_time
            
            # Update statistics
            stats['total_checks'] += 1
            stats['last_check_time'] = time.time()
            
            if health.is_healthy:
                stats['successful_checks'] += 1
                stats['consecutive_failures'] = 0
            else:
                stats['failed_checks'] += 1
                stats['consecutive_failures'] += 1
            
            # Update response time stats
            stats['min_response_time'] = min(stats['min_response_time'], response_time)
            stats['max_response_time'] = max(stats['max_response_time'], response_time)
            
            # Calculate average response time
            if stats['total_checks'] == 1:
                stats['average_response_time'] = response_time
            else:
                stats['average_response_time'] = (
                    (stats['average_response_time'] * (stats['total_checks'] - 1) + response_time) 
                    / stats['total_checks']
                )
            
            # Update health status
            health.response_time = response_time
            health.check_count = stats['total_checks']
            health.consecutive_failures = stats['consecutive_failures']
            
            self.health_status[provider] = health
            
            # Log if health status changed significantly
            if health.is_healthy:
                if stats['consecutive_failures'] == 0 and stats['failed_checks'] > 0:
                    self.logger.info(f"Provider {provider} recovered and is now healthy")
            else:
                self.logger.warning(f"Provider {provider} health check failed: {health.message}")
            
            return health
            
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            stats['total_checks'] += 1
            stats['failed_checks'] += 1
            stats['consecutive_failures'] += 1
            stats['last_check_time'] = time.time()
            
            health = HealthStatus.unhealthy(
                f"Health check timeout after {config.timeout}s",
                status_code=408
            )
            health.response_time = response_time
            health.check_count = stats['total_checks']
            health.consecutive_failures = stats['consecutive_failures']
            
            self.health_status[provider] = health
            self.logger.error(f"Health check timeout for {provider}")
            
            return health
            
        except Exception as e:
            response_time = time.time() - start_time
            stats['total_checks'] += 1
            stats['failed_checks'] += 1
            stats['consecutive_failures'] += 1
            stats['last_check_time'] = time.time()
            
            health = HealthStatus.unhealthy(
                f"Health check error: {e}",
                status_code=500
            )
            health.response_time = response_time
            health.check_count = stats['total_checks']
            health.consecutive_failures = stats['consecutive_failures']
            
            self.health_status[provider] = health
            self.logger.error(f"Health check error for {provider}: {e}")
            
            return health
    
    async def check_all_health(self) -> Dict[str, HealthStatus]:
        """Check health of all registered providers"""
        if not self.health_checkers:
            return {}
        
        # Run all health checks concurrently
        tasks = [
            self.check_health(provider) 
            for provider in self.health_checkers.keys()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dictionary
        health_results = {}
        for provider, result in zip(self.health_checkers.keys(), results):
            if isinstance(result, HealthStatus):
                health_results[provider] = result
            else:
                # Exception occurred
                self.logger.error(f"Health check failed for {provider}: {result}")
                health_results[provider] = HealthStatus.unhealthy(
                    f"Health check exception: {result}"
                )
        
        return health_results
    
    def get_all_health(self) -> Dict[str, HealthStatus]:
        """Get current health status of all providers"""
        return self.health_status.copy()
    
    def get_health(self, provider: str) -> Optional[HealthStatus]:
        """Get current health status of specific provider"""
        return self.health_status.get(provider)
    
    def is_healthy(self, provider: str) -> bool:
        """Check if provider is currently healthy"""
        health = self.health_status.get(provider)
        return health is not None and health.is_healthy
    
    def get_healthy_providers(self) -> List[str]:
        """Get list of currently healthy providers"""
        return [
            provider for provider, health in self.health_status.items()
            if health.is_healthy
        ]
    
    def get_unhealthy_providers(self) -> List[str]:
        """Get list of currently unhealthy providers"""
        return [
            provider for provider, health in self.health_status.items()
            if not health.is_healthy
        ]
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        if self._monitoring_enabled:
            self.logger.warning("Health monitoring already started")
            return
        
        self._monitoring_enabled = True
        self._shutdown_event.clear()
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop continuous health monitoring"""
        if not self._monitoring_enabled:
            return
        
        self._monitoring_enabled = False
        self._shutdown_event.set()
        
        if self._monitoring_task:
            try:
                await asyncio.wait_for(self._monitoring_task, timeout=5.0)
            except asyncio.TimeoutError:
                self.logger.warning("Health monitoring task did not stop gracefully")
                self._monitoring_task.cancel()
        
        self.logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring_enabled:
            try:
                # Check health of all providers
                await self.check_all_health()
                
                # Calculate next check time based on shortest interval
                min_interval = min(
                    (config.interval for config in self.check_configs.values() if config.enabled),
                    default=60.0
                )
                
                # Wait for next check or shutdown
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=min_interval
                    )
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    continue  # Continue monitoring
                    
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5.0)  # Brief pause before retrying
    
    def update_stats(self, provider: str, success: bool, latency: float):
        """Update provider statistics (called by providers)"""
        if provider not in self.provider_stats:
            self.provider_stats[provider] = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'average_latency': 0.0,
                'min_latency': float('inf'),
                'max_latency': 0.0,
                'last_request_time': 0
            }
        
        stats = self.provider_stats[provider]
        stats['total_requests'] += 1
        stats['last_request_time'] = time.time()
        
        if success:
            stats['successful_requests'] += 1
        else:
            stats['failed_requests'] += 1
        
        # Update latency stats
        stats['min_latency'] = min(stats['min_latency'], latency)
        stats['max_latency'] = max(stats['max_latency'], latency)
        
        # Calculate average latency
        if stats['total_requests'] == 1:
            stats['average_latency'] = latency
        else:
            stats['average_latency'] = (
                (stats['average_latency'] * (stats['total_requests'] - 1) + latency) 
                / stats['total_requests']
            )
    
    def get_best_provider(self) -> Optional[str]:
        """Get the best performing healthy provider"""
        healthy_providers = self.get_healthy_providers()
        
        if not healthy_providers:
            return None
        
        if len(healthy_providers) == 1:
            return healthy_providers[0]
        
        # Score providers based on health and performance
        best_provider = None
        best_score = -1
        
        for provider in healthy_providers:
            score = self._calculate_provider_score(provider)
            if score > best_score:
                best_score = score
                best_provider = provider
        
        return best_provider
    
    def _calculate_provider_score(self, provider: str) -> float:
        """Calculate provider score based on health and performance"""
        health = self.health_status.get(provider)
        stats = self.provider_stats.get(provider, {})
        
        if not health or not health.is_healthy:
            return 0.0
        
        score = 100.0  # Base score for healthy provider
        
        # Penalize for slow response times
        response_time = health.response_time
        if response_time > 5.0:
            score -= 30
        elif response_time > 2.0:
            score -= 15
        elif response_time > 1.0:
            score -= 5
        
        # Bonus for successful requests
        total_requests = stats.get('total_requests', 0)
        if total_requests > 0:
            success_rate = stats.get('successful_requests', 0) / total_requests
            score += success_rate * 50
        
        # Penalize for recent failures
        consecutive_failures = health.consecutive_failures
        score -= consecutive_failures * 10
        
        return max(0.0, score)
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary"""
        healthy_count = len(self.get_healthy_providers())
        total_count = len(self.health_status)
        
        return {
            'total_providers': total_count,
            'healthy_providers': healthy_count,
            'unhealthy_providers': total_count - healthy_count,
            'health_percentage': (healthy_count / total_count * 100) if total_count > 0 else 0,
            'monitoring_enabled': self._monitoring_enabled,
            'provider_health': {
                provider: {
                    'is_healthy': health.is_healthy,
                    'message': health.message,
                    'response_time': health.response_time,
                    'last_check': health.last_check.isoformat(),
                    'consecutive_failures': health.consecutive_failures
                }
                for provider, health in self.health_status.items()
            },
            'provider_stats': self.provider_stats
        }
    
    def reset_provider_stats(self, provider: str = None):
        """Reset statistics for provider(s)"""
        if provider:
            if provider in self.provider_stats:
                self.provider_stats[provider] = {
                    'total_checks': 0,
                    'successful_checks': 0,
                    'failed_checks': 0,
                    'consecutive_failures': 0,
                    'last_check_time': 0,
                    'average_response_time': 0.0,
                    'min_response_time': float('inf'),
                    'max_response_time': 0.0
                }
                self.logger.info(f"Reset stats for {provider}")
        else:
            for provider in self.provider_stats:
                self.reset_provider_stats(provider)
            self.logger.info("Reset all provider stats")
