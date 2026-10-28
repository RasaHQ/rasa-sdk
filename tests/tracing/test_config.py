import logging
import threading

import grpc
import pytest

from rasa_sdk.tracing.endpoints import (
    DuplicateTracingConfigException,
    EndpointConfig,
)

from rasa_sdk.tracing import config
from rasa_sdk.tracing.config import JaegerTracerConfigurer
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


def test_get_tracer_provider_list_with_only_langfuse() -> None:
    """Tests that a list containing only a langfuse entry configures no tracing."""
    endpoints_file = str(
        TRACING_TESTS_FIXTURES_DIRECTORY / "langfuse_list_endpoints.yml"
    )

    assert config.get_tracer_provider(endpoints_file) is None


def test_get_tracer_provider_list_skips_langfuse(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests that the OTLP entry is used when listed alongside langfuse."""
    endpoints_file = str(
        TRACING_TESTS_FIXTURES_DIRECTORY / "langfuse_otlp_list_endpoints.yml"
    )

    with caplog.at_level(logging.INFO):
        tracer_provider = config.get_tracer_provider(endpoints_file)

    assert tracer_provider is not None
    assert "Registered otlp endpoint for tracing" in caplog.text
    tracer_provider.shutdown()


def test_get_tracer_provider_single_langfuse_does_not_warn(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests that a single langfuse entry is skipped without a warning."""
    endpoints_file = str(TRACING_TESTS_FIXTURES_DIRECTORY / "langfuse_endpoints.yml")

    with caplog.at_level(logging.WARNING):
        tracer_provider = config.get_tracer_provider(endpoints_file)

    assert tracer_provider is None
    assert "Unknown tracing type" not in caplog.text


def test_get_tracer_provider_list_with_multiple_backends_raises() -> None:
    """Tests that multiple non-langfuse tracing backends are rejected."""
    endpoints_file = str(
        TRACING_TESTS_FIXTURES_DIRECTORY / "jaeger_otlp_list_endpoints.yml"
    )

    with pytest.raises(DuplicateTracingConfigException, match="jaeger, otlp"):
        config.get_tracer_provider(endpoints_file)
