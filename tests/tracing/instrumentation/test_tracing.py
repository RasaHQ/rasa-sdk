import json

import rasa_sdk.endpoint as ep

from typing import Sequence
from opentelemetry.sdk.trace import TracerProvider

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def test_server_webhook_custom_action_is_instrumented(
    tracer_provider: TracerProvider,
    span_exporter: InMemorySpanExporter,
    previous_num_captured_spans: int,
) -> None:
    """Tests that the custom action is instrumented."""
    data = {
        "next_action": "custom_action",
        "version": "1.0.0",
        "tracker": {
            "sender_id": "1",
            "conversation_id": "default",
            "latest_message": {"message_id": "1"},
        },
    }
    app = ep.create_app(None, tracer_provider=tracer_provider)
    _, response = app.test_client.post("/webhook", data=json.dumps(data))

    assert response.status == 200

    captured_spans: Sequence[
        ReadableSpan
    ] = span_exporter.get_finished_spans()  # type: ignore

    num_captured_spans = len(captured_spans) - previous_num_captured_spans
    assert num_captured_spans == 1

    captured_span = captured_spans[-1]

    assert captured_span.attributes == {
        "http.method": "POST",
        "http.route": "/webhook",
        "next_action": data["next_action"],
        "version": data["version"],
        "sender_id": data["tracker"]["sender_id"],
        "message_id": data["tracker"]["latest_message"]["message_id"],
    }


def test_server_webhook_custom_action_is_not_instrumented(
    span_exporter: InMemorySpanExporter,
    previous_num_captured_spans: int,
) -> None:
    """Tests that the server is not instrumented if no tracer provider is provided."""
    data = {
        "next_action": "custom_action",
        "version": "1.0.0",
        "tracker": {
            "sender_id": "1",
            "conversation_id": "default",
            "latest_message": {"message_id": "1"},
        },
    }
    app = ep.create_app(None)
    _, response = app.test_client.post("/webhook", data=json.dumps(data))

    assert response.status == 200

    captured_spans: Sequence[
        ReadableSpan
    ] = span_exporter.get_finished_spans()  # type: ignore

    num_captured_spans = len(captured_spans) - previous_num_captured_spans
    assert num_captured_spans == 0
