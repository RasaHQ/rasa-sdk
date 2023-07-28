import socket

from rasa_sdk.tracing.endpoints import EndpointConfig

from rasa_sdk.tracing import config
from rasa_sdk.tracing.config import JaegerTracerConfigurer
from tests.tracing import conftest
from tests.tracing.conftest import (
    TRACING_TESTS_FIXTURES_DIRECTORY,
)

UDP_BUFFER_SIZE = 2048


def test_jaeger_config_correctly_extracted() -> None:
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
    extracted = JaegerTracerConfigurer._extract_config(EndpointConfig())

    assert extracted["agent_host_name"] == "localhost"
    assert extracted["agent_port"] == 6831
    assert extracted["username"] is None
    assert extracted["password"] is None


def test_get_tracer_provider_jaeger(udp_server: socket.socket) -> None:
    endpoints_file = str(TRACING_TESTS_FIXTURES_DIRECTORY / "jaeger_endpoints.yml")

    tracer_provider = config.get_tracer_provider(endpoints_file)
    assert tracer_provider is not None

    tracer = tracer_provider.get_tracer(__name__)

    with tracer.start_as_current_span("jaeger_test_span"):
        pass

    tracer_provider.force_flush()

    message, _ = udp_server.recvfrom(UDP_BUFFER_SIZE)

    batch = conftest.deserialize_jaeger_batch(bytearray(message))

    assert batch.process.serviceName == "rasa_sdk"

    assert len(batch.spans) == 1
    assert batch.spans[0].operationName == "jaeger_test_span"
