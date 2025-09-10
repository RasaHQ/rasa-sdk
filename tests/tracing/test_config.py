import socket
import threading

import grpc

from rasa_sdk.tracing.endpoints import EndpointConfig

from rasa_sdk.tracing import config
from rasa_sdk.tracing.config import JaegerTracerConfigurer
from tests.tracing import conftest
from tests.tracing.conftest import (
    TRACING_TESTS_FIXTURES_DIRECTORY,
    CapturingTestSpanExporter,
)

UDP_BUFFER_SIZE = 2048


def wait(
    condition: callable,
    result_available_event: threading.Event,
    timeout_seconds: int = 15,
) -> None:
    """Wait for a condition to be true or timeout."""
    result_available_event.wait(timeout_seconds)
    if not condition():
        raise TimeoutError(f"Condition not met within {timeout_seconds} seconds")


def test_jaeger_config_correctly_extracted() -> None:
    """Tests that the Jaeger config is correctly extracted from the endpoint config."""
    cfg = EndpointConfig(
        host="hostname",
        port=1234,
        username="user",
        password="password",
    )

    extracted = JaegerTracerConfigurer._extract_config(cfg)

    assert extracted["agent_host_name"] == cfg.kwargs["host"]
    assert extracted["agent_port"] == cfg.kwargs["port"]
    assert extracted["username"] == cfg.kwargs["username"]
    assert extracted["password"] == cfg.kwargs["password"]


def test_jaeger_config_sets_defaults() -> None:
    """Tests that the Jaeger config sets default config."""
    extracted = JaegerTracerConfigurer._extract_config(EndpointConfig())

    assert extracted["agent_host_name"] == "localhost"
    assert extracted["agent_port"] == 6831
    assert extracted["username"] is None
    assert extracted["password"] is None


def test_get_tracer_provider_jaeger(
    grpc_server: grpc.Server,
    span_exporter: CapturingTestSpanExporter,
    result_available_event: threading.Event,
) -> None:
    """Tests that the tracer provider is correctly configured for Jaeger."""
    endpoints_file = str(TRACING_TESTS_FIXTURES_DIRECTORY / "jaeger_endpoints.yml")

    tracer_provider = config.get_tracer_provider(endpoints_file)
    assert tracer_provider is not None

    tracer = tracer_provider.get_tracer(__name__)

    with tracer.start_as_current_span("jaeger_test_span"):
        pass

    tracer_provider.force_flush()

    wait(
        lambda: span_exporter.spans is not None,
        result_available_event=result_available_event,
        timeout_seconds=15,
    )

    spans = span_exporter.spans
    assert spans is not None
    assert len(spans[0].scope_spans[0].spans) == 1
    assert spans[0].scope_spans[0].spans[0].name == "jaeger_test_span"
