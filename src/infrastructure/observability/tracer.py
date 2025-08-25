"""Distributed tracing support"""

from typing import Optional, Dict, Any, ContextManager
from contextlib import contextmanager
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False


@dataclass
class SpanInfo:
    """Information about a trace span"""
    span_id: str
    trace_id: str
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    tags: Dict[str, Any] = None
    status: str = "ok"  # ok, error, timeout
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


class SimpleTracer:
    """
    Simple tracing implementation when OpenTelemetry is not available.
    
    Provides basic span tracking for debugging and monitoring.
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._active_spans: Dict[str, SpanInfo] = {}
    
    def start_span(
        self, 
        operation_name: str, 
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new span.
        
        Args:
            operation_name: Name of the operation
            parent_span_id: Optional parent span ID
            tags: Optional span tags
            
        Returns:
            Span ID
        """
        span_id = str(uuid.uuid4())
        trace_id = parent_span_id or str(uuid.uuid4())
        
        span = SpanInfo(
            span_id=span_id,
            trace_id=trace_id,
            operation_name=operation_name,
            start_time=datetime.now(timezone.utc),
            tags=tags or {}
        )
        
        self._active_spans[span_id] = span
        return span_id
    
    def finish_span(
        self, 
        span_id: str, 
        status: str = "ok",
        tags: Optional[Dict[str, Any]] = None
    ) -> Optional[SpanInfo]:
        """
        Finish a span.
        
        Args:
            span_id: Span ID to finish
            status: Final span status
            tags: Additional tags to add
            
        Returns:
            Completed SpanInfo or None if span not found
        """
        span = self._active_spans.pop(span_id, None)
        if not span:
            return None
        
        span.end_time = datetime.now(timezone.utc)
        span.status = status
        
        if span.start_time and span.end_time:
            delta = span.end_time - span.start_time
            span.duration_ms = int(delta.total_seconds() * 1000)
        
        if tags:
            span.tags.update(tags)
        
        return span
    
    def add_span_tags(self, span_id: str, tags: Dict[str, Any]) -> None:
        """Add tags to an active span"""
        span = self._active_spans.get(span_id)
        if span:
            span.tags.update(tags)
    
    @contextmanager
    def trace_operation(
        self, 
        operation_name: str, 
        tags: Optional[Dict[str, Any]] = None
    ) -> ContextManager[str]:
        """
        Context manager for tracing an operation.
        
        Args:
            operation_name: Name of the operation
            tags: Optional tags
            
        Yields:
            Span ID
        """
        span_id = self.start_span(operation_name, tags=tags)
        try:
            yield span_id
        except Exception as e:
            self.add_span_tags(span_id, {
                "error": True,
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            self.finish_span(span_id, status="error")
            raise
        else:
            self.finish_span(span_id, status="ok")


class OpenTelemetryTracer:
    """
    OpenTelemetry-based distributed tracing.
    
    Provides full distributed tracing with export to Jaeger or other backends.
    """
    
    def __init__(self, service_name: str, endpoint: Optional[str] = None):
        self.service_name = service_name
        self.endpoint = endpoint
        
        # Configure OpenTelemetry
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        
        if endpoint:
            # Configure Jaeger exporter
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=6831,
            )
            span_processor = BatchSpanProcessor(jaeger_exporter)
            provider.add_span_processor(span_processor)
        
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(service_name)
    
    def start_span(
        self, 
        operation_name: str, 
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Start a new OpenTelemetry span"""
        span = self._tracer.start_span(operation_name)
        
        if tags:
            for key, value in tags.items():
                span.set_attribute(key, value)
        
        return span
    
    def finish_span(
        self, 
        span: Any, 
        status: str = "ok",
        tags: Optional[Dict[str, Any]] = None
    ) -> None:
        """Finish an OpenTelemetry span"""
        if tags:
            for key, value in tags.items():
                span.set_attribute(key, value)
        
        if status == "error":
            span.set_status(trace.Status(trace.StatusCode.ERROR))
        
        span.end()
    
    @contextmanager
    def trace_operation(
        self, 
        operation_name: str, 
        tags: Optional[Dict[str, Any]] = None
    ) -> ContextManager[Any]:
        """Context manager for tracing an operation"""
        with self._tracer.start_as_current_span(operation_name) as span:
            if tags:
                for key, value in tags.items():
                    span.set_attribute(key, value)
            
            try:
                yield span
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                raise


class TracingManager:
    """
    Manages distributed tracing for the application.
    
    Automatically chooses between OpenTelemetry and simple tracing based on availability.
    """
    
    def __init__(
        self, 
        service_name: str, 
        enable_tracing: bool = True,
        endpoint: Optional[str] = None
    ):
        self.service_name = service_name
        self.enable_tracing = enable_tracing
        self.endpoint = endpoint
        
        if enable_tracing and OPENTELEMETRY_AVAILABLE:
            self._tracer = OpenTelemetryTracer(service_name, endpoint)
            self._tracing_type = "opentelemetry"
        elif enable_tracing:
            self._tracer = SimpleTracer(service_name)
            self._tracing_type = "simple"
        else:
            self._tracer = None
            self._tracing_type = "disabled"
    
    @property
    def is_enabled(self) -> bool:
        """Check if tracing is enabled"""
        return self._tracer is not None
    
    @property
    def tracing_type(self) -> str:
        """Get the type of tracing being used"""
        return self._tracing_type
    
    def trace_translation_request(
        self,
        request_id: str,
        provider: str,
        model: str,
        text_length: int
    ) -> ContextManager:
        """
        Trace a translation request.
        
        Args:
            request_id: Unique request ID
            provider: Provider name
            model: Model name
            text_length: Length of text being translated
            
        Returns:
            Context manager for the trace span
        """
        if not self._tracer:
            return self._no_op_context()
        
        tags = {
            "request_id": request_id,
            "provider": provider,
            "model": model,
            "text_length": text_length,
            "operation.type": "translation"
        }
        
        return self._tracer.trace_operation("translation_request", tags)
    
    def trace_provider_call(
        self,
        provider: str,
        model: str,
        request_id: str
    ) -> ContextManager:
        """
        Trace a provider API call.
        
        Args:
            provider: Provider name
            model: Model name
            request_id: Request ID
            
        Returns:
            Context manager for the trace span
        """
        if not self._tracer:
            return self._no_op_context()
        
        tags = {
            "provider": provider,
            "model": model,
            "request_id": request_id,
            "operation.type": "provider_call"
        }
        
        return self._tracer.trace_operation("provider_api_call", tags)
    
    def trace_batch_processing(
        self,
        batch_id: str,
        batch_size: int,
        provider: str
    ) -> ContextManager:
        """
        Trace batch processing.
        
        Args:
            batch_id: Batch ID
            batch_size: Number of requests in batch
            provider: Provider name
            
        Returns:
            Context manager for the trace span
        """
        if not self._tracer:
            return self._no_op_context()
        
        tags = {
            "batch_id": batch_id,
            "batch_size": batch_size,
            "provider": provider,
            "operation.type": "batch_processing"
        }
        
        return self._tracer.trace_operation("batch_translation", tags)
    
    @contextmanager
    def _no_op_context(self):
        """No-op context manager when tracing is disabled"""
        yield None


# Global tracer instance
_tracer: Optional[TracingManager] = None


def get_tracer() -> TracingManager:
    """
    Get the global tracer instance.
    
    Returns:
        TracingManager instance
    """
    global _tracer
    
    if _tracer is None:
        _tracer = TracingManager("ai-translation-framework", enable_tracing=False)
    
    return _tracer


def setup_tracing(
    service_name: str = "ai-translation-framework",
    enable_tracing: bool = True,
    endpoint: Optional[str] = None
) -> TracingManager:
    """
    Setup and configure distributed tracing.
    
    Args:
        service_name: Name of the service
        enable_tracing: Whether to enable tracing
        endpoint: Optional tracing endpoint
        
    Returns:
        Configured TracingManager instance
    """
    global _tracer
    
    _tracer = TracingManager(service_name, enable_tracing, endpoint)
    return _tracer