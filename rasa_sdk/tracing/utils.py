from multidict import MultiDict

from rasa_sdk.tracing import config
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from opentelemetry.sdk.trace import TracerProvider

from typing import Optional, Tuple, Any


def get_tracer_provider(endpoints_file: str) -> Optional[TracerProvider]:
    """Gets the tracer provider from the command line arguments."""
    tracer_provider = config.get_tracer_provider(endpoints_file)
    config.configure_tracing(tracer_provider)

    return tracer_provider


def get_tracer_and_context(
    span_name: str,
    tracer_provider: Optional[TracerProvider],
    tracing_carrier: Optional[MultiDict],
) -> Tuple[Any, Any]:
    """Gets tracer and context."""
    if tracer_provider is None:
        tracer = trace.get_tracer(span_name)
        context = None
    else:
        tracer = tracer_provider.get_tracer(span_name)
        context = (
            TraceContextTextMapPropagator().extract(tracing_carrier)
            if tracing_carrier
            else None
        )
    return tracer, context


def set_span_attributes(span: Any, action_call: dict) -> None:
    """Sets span attributes."""
    tracker = action_call.get("tracker", {})
    span_attributes = {
        "next_action": action_call.get("next_action"),
        "version": action_call.get("version"),
        "sender_id": tracker.get("sender_id"),
        "message_id": tracker.get("latest_message", {}).get("message_id", "None"),
    }

    if span.is_recording():
        for key, value in span_attributes.items():
            span.set_attribute(key, value)

    return None
