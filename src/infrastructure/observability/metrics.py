"""Metrics collection and reporting"""

from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import time
import threading
from collections import defaultdict, Counter

try:
    from prometheus_client import Counter as PrometheusCounter, Histogram, Gauge, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class MetricType(str, Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge" 
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricValue:
    """A metric measurement"""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metric_type: MetricType = MetricType.GAUGE


class MetricsCollector:
    """
    Collects and manages application metrics.
    
    Provides a simple interface for recording metrics with optional Prometheus integration.
    """
    
    def __init__(self, enable_prometheus: bool = True):
        """
        Initialize metrics collector.
        
        Args:
            enable_prometheus: Whether to enable Prometheus metrics
        """
        self.enable_prometheus = enable_prometheus and PROMETHEUS_AVAILABLE
        self._lock = threading.Lock()
        
        # In-memory metrics storage
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._labels: Dict[str, Dict[str, str]] = {}
        
        # Prometheus metrics
        if self.enable_prometheus:
            self._registry = CollectorRegistry()
            self._prometheus_counters: Dict[str, PrometheusCounter] = {}
            self._prometheus_gauges: Dict[str, Gauge] = {}
            self._prometheus_histograms: Dict[str, Histogram] = {}
        
        # Built-in metrics
        self._setup_builtin_metrics()
    
    def _setup_builtin_metrics(self) -> None:
        """Setup built-in application metrics"""
        
        # Translation metrics
        self.create_counter(
            "translation_requests_total",
            "Total number of translation requests",
            labels=["provider", "model", "status"]
        )
        
        self.create_histogram(
            "translation_duration_seconds",
            "Translation request duration in seconds",
            labels=["provider", "model"]
        )
        
        self.create_counter(
            "translation_tokens_total",
            "Total tokens processed",
            labels=["provider", "model", "type"]  # type: input/output
        )
        
        self.create_counter(
            "translation_errors_total",
            "Total translation errors",
            labels=["provider", "error_type"]
        )
        
        # Provider metrics
        self.create_gauge(
            "provider_health_status",
            "Provider health status (1=healthy, 0=unhealthy)",
            labels=["provider"]
        )
        
        self.create_counter(
            "provider_api_calls_total",
            "Total API calls to providers",
            labels=["provider", "status_code"]
        )
        
        # Rate limiting metrics
        self.create_counter(
            "rate_limit_hits_total",
            "Total rate limit hits",
            labels=["provider", "limit_type"]
        )
        
        # System metrics
        self.create_gauge(
            "active_requests",
            "Number of active translation requests"
        )
        
        self.create_histogram(
            "request_queue_time_seconds",
            "Time requests spend in queue"
        )
    
    def create_counter(
        self, 
        name: str, 
        description: str = "", 
        labels: Optional[List[str]] = None
    ) -> None:
        """
        Create a counter metric.
        
        Args:
            name: Metric name
            description: Metric description
            labels: Optional list of label names
        """
        labels = labels or []
        
        if self.enable_prometheus:
            self._prometheus_counters[name] = PrometheusCounter(
                name, description, labels, registry=self._registry
            )
        
        self._labels[name] = {}
    
    def create_gauge(
        self, 
        name: str, 
        description: str = "", 
        labels: Optional[List[str]] = None
    ) -> None:
        """
        Create a gauge metric.
        
        Args:
            name: Metric name
            description: Metric description
            labels: Optional list of label names
        """
        labels = labels or []
        
        if self.enable_prometheus:
            self._prometheus_gauges[name] = Gauge(
                name, description, labels, registry=self._registry
            )
        
        self._labels[name] = {}
    
    def create_histogram(
        self, 
        name: str, 
        description: str = "", 
        labels: Optional[List[str]] = None,
        buckets: Optional[List[float]] = None
    ) -> None:
        """
        Create a histogram metric.
        
        Args:
            name: Metric name
            description: Metric description
            labels: Optional list of label names
            buckets: Optional histogram buckets
        """
        labels = labels or []
        
        if self.enable_prometheus:
            kwargs = {"registry": self._registry}
            if buckets:
                kwargs["buckets"] = buckets
            
            self._prometheus_histograms[name] = Histogram(
                name, description, labels, **kwargs
            )
        
        self._labels[name] = {}
    
    def increment_counter(
        self, 
        name: str, 
        value: float = 1.0, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Counter name
            value: Value to add
            labels: Optional labels
        """
        labels = labels or {}
        
        with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] += value
        
        if self.enable_prometheus and name in self._prometheus_counters:
            if labels:
                self._prometheus_counters[name].labels(**labels).inc(value)
            else:
                self._prometheus_counters[name].inc(value)
    
    def set_gauge(
        self, 
        name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Set a gauge metric value.
        
        Args:
            name: Gauge name
            value: Value to set
            labels: Optional labels
        """
        labels = labels or {}
        
        with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value
        
        if self.enable_prometheus and name in self._prometheus_gauges:
            if labels:
                self._prometheus_gauges[name].labels(**labels).set(value)
            else:
                self._prometheus_gauges[name].set(value)
    
    def observe_histogram(
        self, 
        name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Observe a value in a histogram.
        
        Args:
            name: Histogram name
            value: Value to observe
            labels: Optional labels
        """
        labels = labels or {}
        
        with self._lock:
            key = self._make_key(name, labels)
            self._histograms[key].append(value)
        
        if self.enable_prometheus and name in self._prometheus_histograms:
            if labels:
                self._prometheus_histograms[name].labels(**labels).observe(value)
            else:
                self._prometheus_histograms[name].observe(value)
    
    def time_operation(self, metric_name: str, labels: Optional[Dict[str, str]] = None):
        """
        Context manager to time an operation.
        
        Args:
            metric_name: Histogram metric to record duration
            labels: Optional labels
            
        Returns:
            Context manager that records operation duration
        """
        return _TimingContext(self, metric_name, labels)
    
    def record_translation_request(
        self,
        provider: str,
        model: str,
        status: str,
        duration_seconds: float,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None
    ) -> None:
        """
        Record metrics for a translation request.
        
        Args:
            provider: Provider name
            model: Model name
            status: Request status (success/error)
            duration_seconds: Request duration
            input_tokens: Input tokens used
            output_tokens: Output tokens generated
        """
        labels = {"provider": provider, "model": model, "status": status}
        
        self.increment_counter("translation_requests_total", labels=labels)
        self.observe_histogram("translation_duration_seconds", duration_seconds, 
                             labels={"provider": provider, "model": model})
        
        if input_tokens:
            self.increment_counter(
                "translation_tokens_total", 
                value=input_tokens,
                labels={"provider": provider, "model": model, "type": "input"}
            )
        
        if output_tokens:
            self.increment_counter(
                "translation_tokens_total", 
                value=output_tokens,
                labels={"provider": provider, "model": model, "type": "output"}
            )
    
    def record_provider_health(self, provider: str, is_healthy: bool) -> None:
        """Record provider health status"""
        self.set_gauge(
            "provider_health_status",
            1.0 if is_healthy else 0.0,
            labels={"provider": provider}
        )
    
    def record_rate_limit_hit(self, provider: str, limit_type: str) -> None:
        """Record a rate limit hit"""
        self.increment_counter(
            "rate_limit_hits_total",
            labels={"provider": provider, "limit_type": limit_type}
        )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current metrics.
        
        Returns:
            Dictionary with metric summaries
        """
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histogram_counts": {k: len(v) for k, v in self._histograms.items()},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def get_prometheus_metrics(self) -> Optional[bytes]:
        """
        Get Prometheus-formatted metrics.
        
        Returns:
            Prometheus metrics in text format, or None if Prometheus is disabled
        """
        if not self.enable_prometheus:
            return None
        
        return generate_latest(self._registry)
    
    def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing)"""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
    
    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        """Create a unique key for a metric with labels"""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}[{label_str}]"


class _TimingContext:
    """Context manager for timing operations"""
    
    def __init__(self, collector: MetricsCollector, metric_name: str, labels: Optional[Dict[str, str]]):
        self.collector = collector
        self.metric_name = metric_name
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.observe_histogram(self.metric_name, duration, self.labels)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """
    Get the global metrics collector instance.
    
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    
    return _metrics_collector


def setup_metrics(enable_prometheus: bool = True) -> MetricsCollector:
    """
    Setup and configure the global metrics collector.
    
    Args:
        enable_prometheus: Whether to enable Prometheus metrics
        
    Returns:
        Configured MetricsCollector instance
    """
    global _metrics_collector
    
    _metrics_collector = MetricsCollector(enable_prometheus=enable_prometheus)
    return _metrics_collector