"""
Metrics service for tracking performance, error rates, and system statistics.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field
from statistics import mean, median

from ..core.interfaces import IMetricsService


@dataclass
class CounterMetric:
    """Counter metric that only increases"""
    name: str
    value: int = 0
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)


@dataclass  
class GaugeMetric:
    """Gauge metric that can increase or decrease"""
    name: str
    value: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)


@dataclass
class HistogramMetric:
    """Histogram metric for tracking distributions"""
    name: str
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    
    def add_value(self, value: float):
        self.values.append(value)
        self.last_updated = time.time()
    
    def get_stats(self) -> Dict[str, float]:
        if not self.values:
            return {}
        
        values_list = list(self.values)
        return {
            "count": len(values_list),
            "sum": sum(values_list),
            "min": min(values_list),
            "max": max(values_list),
            "mean": mean(values_list),
            "median": median(values_list)
        }


class MetricsService(IMetricsService):
    """Service for collecting and managing metrics"""
    
    def __init__(self):
        self._counters: Dict[str, CounterMetric] = {}
        self._gauges: Dict[str, GaugeMetric] = {}
        self._histograms: Dict[str, HistogramMetric] = {}
        self._lock = asyncio.Lock()
        
        # Built-in metrics
        self._start_time = time.time()
        self._request_count = 0
        self._error_count = 0
    
    def _metric_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """Generate unique key for metric with tags"""
        if not tags:
            return name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"
    
    def increment_counter(self, name: str, tags: Dict[str, str] = None, value: int = 1) -> None:
        """Increment counter metric"""
        key = self._metric_key(name, tags)
        
        if key not in self._counters:
            self._counters[key] = CounterMetric(name=name, tags=tags or {})
        
        self._counters[key].value += value
        self._counters[key].last_updated = time.time()
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Set gauge metric value"""
        key = self._metric_key(name, tags)
        
        if key not in self._gauges:
            self._gauges[key] = GaugeMetric(name=name, tags=tags or {})
        
        self._gauges[key].value = value
        self._gauges[key].last_updated = time.time()
    
    def record_duration(self, name: str, duration: float, tags: Dict[str, str] = None) -> None:
        """Record duration in histogram"""
        key = self._metric_key(name, tags)
        
        if key not in self._histograms:
            self._histograms[key] = HistogramMetric(name=name, tags=tags or {})
        
        self._histograms[key].add_value(duration)
    
    def record_value(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record arbitrary value in histogram"""
        self.record_duration(name, value, tags)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        now = time.time()
        uptime = now - self._start_time
        
        result = {
            "timestamp": now,
            "uptime_seconds": uptime,
            "counters": {},
            "gauges": {},
            "histograms": {}
        }
        
        # Add counters
        for key, counter in self._counters.items():
            result["counters"][key] = {
                "name": counter.name,
                "value": counter.value,
                "tags": counter.tags,
                "created_at": counter.created_at,
                "last_updated": counter.last_updated
            }
        
        # Add gauges
        for key, gauge in self._gauges.items():
            result["gauges"][key] = {
                "name": gauge.name,
                "value": gauge.value,
                "tags": gauge.tags,
                "created_at": gauge.created_at,
                "last_updated": gauge.last_updated
            }
        
        # Add histograms
        for key, histogram in self._histograms.items():
            result["histograms"][key] = {
                "name": histogram.name,
                "tags": histogram.tags,
                "created_at": histogram.created_at,
                "last_updated": histogram.last_updated,
                "stats": histogram.get_stats()
            }
        
        return result
    
    def get_counter(self, name: str, tags: Dict[str, str] = None) -> Optional[int]:
        """Get counter value"""
        key = self._metric_key(name, tags)
        counter = self._counters.get(key)
        return counter.value if counter else None
    
    def get_gauge(self, name: str, tags: Dict[str, str] = None) -> Optional[float]:
        """Get gauge value"""
        key = self._metric_key(name, tags)
        gauge = self._gauges.get(key)
        return gauge.value if gauge else None
    
    def get_histogram_stats(self, name: str, tags: Dict[str, str] = None) -> Optional[Dict[str, float]]:
        """Get histogram statistics"""
        key = self._metric_key(name, tags)
        histogram = self._histograms.get(key)
        return histogram.get_stats() if histogram else None
    
    def reset_metrics(self) -> None:
        """Reset all metrics"""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._start_time = time.time()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        now = time.time()
        
        return {
            "uptime_seconds": now - self._start_time,
            "total_counters": len(self._counters),
            "total_gauges": len(self._gauges),
            "total_histograms": len(self._histograms),
            "last_updated": max([
                max([c.last_updated for c in self._counters.values()] + [0]),
                max([g.last_updated for g in self._gauges.values()] + [0]),
                max([h.last_updated for h in self._histograms.values()] + [0])
            ]) if any([self._counters, self._gauges, self._histograms]) else self._start_time
        }


# Context manager for timing operations
class TimedOperation:
    """Context manager for timing operations and recording to metrics"""
    
    def __init__(self, metrics_service: MetricsService, name: str, tags: Dict[str, str] = None):
        self.metrics_service = metrics_service
        self.name = name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.metrics_service.record_duration(self.name, duration, self.tags)
            
            # Also record success/failure
            if exc_type is None:
                self.metrics_service.increment_counter(f"{self.name}.success", self.tags)
            else:
                self.metrics_service.increment_counter(f"{self.name}.error", self.tags)