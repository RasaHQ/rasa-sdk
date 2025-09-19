import logging
import importlib
import os
from typing import Text, List, Tuple

import grpc
import pytest

from google.protobuf.json_format import MessageToDict
from grpc_health.v1 import health_pb2
from grpc_health.v1.health_pb2_grpc import HealthStub

try:
    # Try to import pb5 (protobuf >= 5)
    action_webhook_pb2_grpc = importlib.import_module("rasa_sdk.grpc_py.pb5.action_webhook_pb2_grpc")
    action_webhook_pb2 = importlib.import_module("rasa_sdk.grpc_py.pb5.action_webhook_pb2")
except ModuleNotFoundError:
    # Fallback to pb4 (protobuf < 5)
    action_webhook_pb2_grpc = importlib.import_module("rasa_sdk.grpc_py.pb4.action_webhook_pb2_grpc")
    action_webhook_pb2 = importlib.import_module("rasa_sdk.grpc_py.pb4.action_webhook_pb2")

from rasa_sdk.grpc_server import GRPC_ACTION_SERVER_NAME
from integration_tests.conftest import ca_cert, client_key, client_cert

GRPC_HOST = os.getenv("GRPC_ACTION_SERVER_HOST", "localhost")
GRPC_NO_TLS_PORT = os.getenv("GRPC_NO_TLS_PORT", 7010)
GRPC_TLS_HOST = os.getenv("GRPC_ACTION_SERVER_TLS_HOST", "localhost")
GRPC_TLS_PORT = os.getenv("GRPC_TLS_PORT", 7011)
GRPC_REQUEST_TIMEOUT_IN_SECONDS = os.getenv("GRPC_REQUEST_TIMEOUT_IN_SECONDS", 5)

logger = logging.getLogger(__name__)


def create_no_tls_channel() -> grpc.Channel:
    """Create a gRPC channel for the action server."""
    logger.info(f"Creating insecure channel to {GRPC_HOST}:{GRPC_NO_TLS_PORT}")

    return grpc.insecure_channel(
        target=f"{GRPC_HOST}:{GRPC_NO_TLS_PORT}",
        compression=grpc.Compression.Gzip)


def create_tls_channel(
) -> grpc.Channel:
    """Create a gRPC channel for the action server."""
    credentials = grpc.ssl_channel_credentials(
        root_certificates=ca_cert(),
        private_key=client_key(),
        certificate_chain=client_cert(),
    )

    logger.info(f"Creating secure channel to {GRPC_TLS_HOST}:{GRPC_TLS_PORT}")
    return grpc.secure_channel(
        target=f"{GRPC_TLS_HOST}:{GRPC_TLS_PORT}",
        credentials=credentials,
        compression=grpc.Compression.Gzip)


GrpcMetadata = List[Tuple[Text, Text]]


@pytest.fixture(scope='session')
def grpc_metadata() -> GrpcMetadata:
    return [('test-key', 'test-value')]


@pytest.fixture(scope='session')
def grpc_webhook_request() -> action_webhook_pb2.WebhookRequest:
    return action_webhook_pb2.WebhookRequest(
        next_action="action_hi",
        sender_id="test_sender_id",
        version="test_version",
        domain_digest="test_domain_digest",
        tracker=action_webhook_pb2.Tracker(
            sender_id="test_sender_id",
            slots={},
            latest_message={},
            events=[],
            paused=False,
            followup_action="",
            active_loop={},
            latest_action_name="",
            stack={},
        ),
        domain=action_webhook_pb2.Domain(
            config={},
            session_config={},
            intents=[],
            entities=[],
            slots={},
            responses={},
            actions=[],
            forms={},
            e2e_actions=[],
        ),
    )


@pytest.mark.parametrize("grpc_channel", [
    create_no_tls_channel(),
    create_tls_channel(),
])
def test_grpc_server_webhook(
    grpc_channel: grpc.Channel,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    grpc_metadata: GrpcMetadata,
) -> None:
    """Test Webhook invocation of the gRPC server."""

    client = action_webhook_pb2_grpc.ActionServiceStub(grpc_channel)

    # Invoke Webhook method
    rpc_response = client.Webhook(
        grpc_webhook_request,
        metadata=grpc_metadata,
        timeout=GRPC_REQUEST_TIMEOUT_IN_SECONDS,
        wait_for_ready=True,
    )

    response = MessageToDict(
        rpc_response,
    )

    # Verify the response
    assert set(response.keys()) == {'responses'}
    assert len(response['responses']) == 1
    assert response['responses'][0]['text'] == 'Hi'


@pytest.mark.parametrize("grpc_channel", [
    create_no_tls_channel(),
    create_tls_channel(),
])
def test_grpc_server_healthcheck(
    grpc_channel: grpc.Channel,
) -> None:
    """Test healthcheck endpoint of the gRPC server."""
    client = HealthStub(grpc_channel)

    response = client.Check(
        health_pb2.HealthCheckRequest(service=GRPC_ACTION_SERVER_NAME),
        wait_for_ready=True,
        timeout=GRPC_REQUEST_TIMEOUT_IN_SECONDS,
    )
    assert response.status == health_pb2.HealthCheckResponse.SERVING
