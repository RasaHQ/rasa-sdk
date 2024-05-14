import json
from functools import partial

import pytest

import rasa_sdk.endpoint as ep

from typing import Sequence
from opentelemetry.sdk.trace import TracerProvider
from pytest import MonkeyPatch

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


data = {
    "version": "1.0.0",
    "sender_id": "1",
    "tracker": {
        "sender_id": "1",
        "conversation_id": "default",
        "latest_message": {"message_id": "1"},
    },
    "domain": {},
}


@pytest.mark.parametrize(
    "action_name, action_package",
    [
        ("dummy_action", "action_fixtures"),
        ("", None),
    ],
)
def test_server_webhook_custom_action_is_instrumented(
    tracer_provider: TracerProvider,
    span_exporter: InMemorySpanExporter,
    previous_num_captured_spans: int,
    action_name: str,
    action_package: str,
    monkeypatch: MonkeyPatch,
) -> None:
    """Tests that the custom action is instrumented."""
    monkeypatch.setattr(
        "rasa_sdk.endpoint.get_tracer_provider", lambda _: tracer_provider
    )
    data["next_action"] = action_name
    app = ep.create_app(action_package)

    app.register_listener(
        partial(ep.load_tracer_provider, endpoints="endpoints.yml"),
        "main_process_start",
    )

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


@pytest.mark.parametrize(
    "action_name, action_package",
    [
        ("dummy_action", "action_fixtures"),
        ("", None),
    ],
)
def test_server_webhook_custom_action_is_not_instrumented(
    span_exporter: InMemorySpanExporter,
    previous_num_captured_spans: int,
    action_name: str,
    action_package: str,
) -> None:
    """Tests that the server is not instrumented if no tracer provider is provided."""
    data["next_action"] = action_name
    app = ep.create_app(action_package)
    _, response = app.test_client.post("/webhook", data=json.dumps(data))

    assert response.status == 200

    captured_spans: Sequence[
        ReadableSpan
    ] = span_exporter.get_finished_spans()  # type: ignore

    num_captured_spans = len(captured_spans) - previous_num_captured_spans
    assert num_captured_spans == 0
