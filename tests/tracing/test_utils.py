import json
import argparse

import rasa_sdk.endpoint as ep

from opentelemetry.trace import ProxyTracer
from opentelemetry.sdk.trace import TracerProvider

from rasa_sdk.tracing.utils import (
    get_tracer_provider,
    get_tracer_and_context,
)

from tests.tracing.conftest import (
    TRACING_TESTS_FIXTURES_DIRECTORY,
)


def test_get_tracer_provider_returns_none_if_no_endpoints_file() -> None:
    """Tests that get_tracer_provider returns None if no endpoints file is provided."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--random_args", type=str, default=None)

    args = parser.parse_args(["--random_args", "random text"])

    tracer_provider = get_tracer_provider(args)

    assert tracer_provider is None


def test_get_tracer_provider_returns_none_if_tracing_is_not_configured() -> None:
    """Tests that get_tracer_provider returns None if tracing is not configured."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoints", type=str, default=None)

    endpoints_file = str(TRACING_TESTS_FIXTURES_DIRECTORY / "no_tracing.yml")
    args = parser.parse_args(["--endpoints", endpoints_file])

    tracer_provider = get_tracer_provider(args)

    assert tracer_provider is None


def test_get_tracer_provider_returns_provider() -> None:
    """Tests that get_tracer_provider returns a TracerProvider
    if tracing is configured."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoints", type=str, default=None)

    endpoints_file = str(TRACING_TESTS_FIXTURES_DIRECTORY / "jaeger_endpoints.yml")
    args = parser.parse_args(["--endpoints", endpoints_file])

    tracer_provider = get_tracer_provider(args)

    assert tracer_provider is not None
    assert isinstance(tracer_provider, TracerProvider)


def test_get_tracer_and_context() -> None:
    """Tests that get_tracer_and_context returns a ProxyTracer and span name"""
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
    request, _ = app.test_client.post("/webhook", data=json.dumps(data))
    tracer, context, span_name = get_tracer_and_context(None, request)
    print(type(tracer))

    assert isinstance(tracer, ProxyTracer)
    assert span_name == "create_app.webhook"
    assert context is None
