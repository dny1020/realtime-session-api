"""
OpenTelemetry tracing configuration for distributed tracing

Provides end-to-end visibility across microservices.
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from loguru import logger

from config.settings import get_settings

settings = get_settings()


def setup_tracing(app):
    """
    Initialize OpenTelemetry tracing for the application
    
    Call this during application startup
    """
    if not settings.otel_enabled:
        logger.info("OpenTelemetry tracing is disabled")
        return
    
    try:
        # Create resource with service information
        resource = Resource.create({
            SERVICE_NAME: settings.otel_service_name,
            "service.version": settings.app_version,
            "deployment.environment": "production" if not settings.debug else "development"
        })
        
        # Set up tracer provider
        provider = TracerProvider(resource=resource)
        
        # Configure OTLP exporter (sends to Jaeger, Tempo, etc.)
        if settings.otel_endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.otel_endpoint,
                insecure=settings.debug  # Use insecure in dev only
            )
            
            # Add batch processor for efficiency
            processor = BatchSpanProcessor(otlp_exporter)
            provider.add_span_processor(processor)
        
        # Set as global tracer provider
        trace.set_tracer_provider(provider)
        
        # Instrument FastAPI automatically
        FastAPIInstrumentor.instrument_app(app)
        
        # Instrument SQLAlchemy
        try:
            from app.database import engine
            if engine:
                SQLAlchemyInstrumentor().instrument(
                    engine=engine,
                    service=settings.otel_service_name
                )
        except Exception as e:
            logger.warning(f"Failed to instrument SQLAlchemy: {e}")
        
        # Instrument Redis
        RedisInstrumentor().instrument()
        
        logger.info(
            "OpenTelemetry tracing initialized",
            extra={
                "service": settings.otel_service_name,
                "endpoint": settings.otel_endpoint
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
        # Don't fail application startup if tracing fails


def get_tracer(name: str = None):
    """
    Get a tracer instance for creating custom spans
    
    Usage:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("operation_name"):
            # Code to trace
            ...
    """
    if not settings.otel_enabled:
        # Return no-op tracer if tracing is disabled
        from opentelemetry.trace import NoOpTracer
        return NoOpTracer()
    
    return trace.get_tracer(name or settings.otel_service_name)


def add_span_attributes(**attributes):
    """
    Add custom attributes to current span
    
    Usage:
        add_span_attributes(
            call_id="abc123",
            phone_number="+1234567890",
            status="completed"
        )
    """
    if not settings.otel_enabled:
        return
    
    try:
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            for key, value in attributes.items():
                current_span.set_attribute(key, value)
    except Exception as e:
        logger.debug(f"Failed to add span attributes: {e}")


def record_exception(exception: Exception):
    """
    Record exception in current span
    
    Usage:
        try:
            risky_operation()
        except Exception as e:
            record_exception(e)
            raise
    """
    if not settings.otel_enabled:
        return
    
    try:
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.record_exception(exception)
            current_span.set_status(trace.Status(trace.StatusCode.ERROR))
    except Exception as e:
        logger.debug(f"Failed to record exception in span: {e}")
