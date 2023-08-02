import argparse
from rasa_sdk.tracing import config
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from opentelemetry.sdk.trace import TracerProvider
from sanic.request import Request

from typing import Optional, Tuple, Any, Text


def get_tracer_provider(
    cmdline_arguments: argparse.Namespace,
) -> Optional[TracerProvider]:
    """Gets the tracer provider from the command line arguments."""
    tracer_provider = None
    endpoints_file = ""
    if "endpoints" in cmdline_arguments:
        endpoints_file = cmdline_arguments.endpoints

    if endpoints_file is not None:
        tracer_provider = config.get_tracer_provider(endpoints_file)
    return tracer_provider


def get_tracer_and_context(
    tracer_provider: Optional[TracerProvider], request: Request
) -> Tuple[Any, Any, Text]:
    """Gets tracer and context"""
    span_name = "rasa_sdk.create_app.webhook"
    if tracer_provider is None:
        tracer = trace.get_tracer(span_name)
        context = None
    else:
        tracer = tracer_provider.get_tracer(span_name)
        context = TraceContextTextMapPropagator().extract(request.headers)
    return (tracer, context, span_name)


def set_span_attributes(span: Any, action_call: dict) -> None:
    """Sets span attributes"""
    tracker = action_call.get("tracker", {})
    set_span_attributes = {
        "http.method": "POST",
        "http.route": "/webhook",
        "next_action": action_call.get("next_action"),
        "version": action_call.get("version"),
        "sender_id": tracker.get("sender_id"),
        "message_id": tracker.get("latest_message", {}).get("message_id"),
    }

    if span.is_recording():
        for key, value in set_span_attributes.items():
            span.set_attribute(key, value)

    return None
