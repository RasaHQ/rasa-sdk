import asyncio
import threading
from typing import Text, List, Tuple, Set, Union
from unittest.mock import AsyncMock

import grpc
import pytest

from google.protobuf.json_format import MessageToDict
from grpc_health.v1 import health_pb2
from grpc_health.v1.health_pb2_grpc import HealthStub

from rasa_sdk.executor import ActionExecutor, ActionExecutorRunResult
from rasa_sdk.grpc_errors import ResourceNotFound, ResourceNotFoundType
from rasa_sdk.grpc_py import action_webhook_pb2_grpc, action_webhook_pb2
from rasa_sdk.grpc_server import GRPC_ACTION_SERVER_NAME, _initialise_grpc_server
from rasa_sdk.interfaces import ActionNotFoundException, ActionMissingDomainException
from integration_tests.conftest import server_cert, server_cert_key, ca_cert, client_key, client_cert

GRPC_PORT = 6000
GRPC_TLS_PORT = 6001
GRPC_HOST = 'localhost'


@pytest.fixture(scope="module")
def mock_executor() -> AsyncMock:
    """Create a mock action executor."""
    return AsyncMock(spec=ActionExecutor)


@pytest.fixture(scope="module")
def grpc_action_server(mock_executor: AsyncMock) -> None:
    """Create a gRPC server for the action server."""

    _event = asyncio.Event()

    async def _run_grpc_server() -> None:
        _grpc_action_server = _initialise_grpc_server(
            action_executor=mock_executor,
            port=GRPC_PORT,
            max_number_of_workers=2,
        )
        await _grpc_action_server.start()
        await _event.wait()
        await _grpc_action_server.stop(None)

    thread = threading.Thread(target=asyncio.run, args=(_run_grpc_server(),), daemon=True)
    thread.start()
    yield
    _event.set()


@pytest.fixture(scope="module")
def grpc_tls_action_server(mock_executor: AsyncMock) -> None:
    """Create a gRPC server for the action server."""

    _event = asyncio.Event()

    async def _run_grpc_server() -> None:
        _grpc_action_server = _initialise_grpc_server(
            action_executor=mock_executor,
            port=GRPC_TLS_PORT,
            max_number_of_workers=2,
            ssl_server_cert=server_cert(),
            ssl_server_cert_key=server_cert_key(),
        )
        await _grpc_action_server.start()
        await _event.wait()
        await _grpc_action_server.stop(None)

    thread = threading.Thread(target=asyncio.run, args=(_run_grpc_server(),), daemon=True)
    thread.start()
    yield
    _event.set()


@pytest.fixture
def grpc_channel() -> grpc.Channel:
    """Create a gRPC channel for the action server."""
    return grpc.insecure_channel(target=f"{GRPC_HOST}:{GRPC_PORT}", compression=grpc.Compression.Gzip)


@pytest.fixture
def grpc_action_client(grpc_channel: grpc.Channel) -> action_webhook_pb2_grpc.ActionServiceStub:
    """Create a gRPC client for the action server."""
    client = action_webhook_pb2_grpc.ActionServiceStub(grpc_channel)
    return client


@pytest.fixture
def grpc_tls_channel() -> grpc.Channel:
    """Create a gRPC channel for the action server."""
    credentials = grpc.ssl_channel_credentials(
        root_certificates=ca_cert(),
        private_key=client_key(),
        certificate_chain=client_cert(),
    )
    return grpc.secure_channel(
        target=f"{GRPC_HOST}:{GRPC_TLS_PORT}",
        compression=grpc.Compression.Gzip,
        credentials=credentials,
    )


@pytest.fixture
def grpc_tls_action_client(grpc_tls_channel: grpc.Channel) -> action_webhook_pb2_grpc.ActionServiceStub:
    """Create a gRPC client for the action server."""
    client = action_webhook_pb2_grpc.ActionServiceStub(grpc_tls_channel)
    return client


GrpcMetadata = List[Tuple[Text, Text]]


@pytest.fixture
def grpc_metadata() -> GrpcMetadata:
    return [('test-key', 'test-value')]


@pytest.fixture
def grpc_webhook_request() -> action_webhook_pb2.WebhookRequest:
    return action_webhook_pb2.WebhookRequest(
        next_action="action_listen",
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


@pytest.mark.usefixtures("grpc_action_server", "grpc_tls_action_server")
@pytest.mark.parametrize(
    "executor_result, expected_keys", [
    (
        ActionExecutorRunResult(
            events=[],
            responses=[],
        ),
        set(),
    ),
    (
        ActionExecutorRunResult(
            events=[],
            responses=[{"recipient_id": "test_sender_id", "text": "test_response"}],
        ),
        {"responses"},
    ),
    (
        ActionExecutorRunResult(
            events=[{"event": "action", "name": "action_listen"}],
            responses=[],
        ),
        {"events"},
    ),
    (
        ActionExecutorRunResult(
            events=[{"event": "action", "name": "action_listen"}],
            responses=[{"recipient_id": "test_sender_id", "text": "test_response"}],
        ),
        {"events", "responses"},
    ),
])
@pytest.mark.parametrize("action_client_name", ["grpc_action_client", "grpc_tls_action_client"])
def test_grpc_server_webhook(
    action_client_name: str,
    executor_result: ActionExecutorRunResult,
    expected_keys: Set[str],
    mock_executor: AsyncMock,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    grpc_metadata: GrpcMetadata,
    request: pytest.FixtureRequest,
) -> None:
    """Test connectivity to the gRPC server without SSL."""
    action_client = request.getfixturevalue(action_client_name)

    # Given a mock executor
    mock_executor.run.return_value = executor_result

    # Invoke Webhook method
    rpc_response = action_client.Webhook(
        grpc_webhook_request,
        metadata=grpc_metadata,
        timeout=5,
        wait_for_ready=True,
    )

    response = MessageToDict(
        rpc_response,
    )

    # Verify the response
    assert set(response.keys()) == expected_keys
    assert response.get("events", []) == executor_result.events
    assert response.get("responses", []) == executor_result.responses


@pytest.mark.usefixtures("grpc_action_server", "grpc_tls_action_server")
@pytest.mark.parametrize("exception, resource_type", [
    (ActionMissingDomainException("test_action"), ResourceNotFoundType.DOMAIN),
    (ActionNotFoundException("test_action"), ResourceNotFoundType.ACTION),
])
@pytest.mark.parametrize("action_client_name", ["grpc_action_client", "grpc_tls_action_client"])
def test_grpc_server_action_missing_domain(
    action_client_name: str,
    exception: Union[ActionMissingDomainException, ActionNotFoundException],
    resource_type: ResourceNotFoundType,
    mock_executor: AsyncMock,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    grpc_metadata: GrpcMetadata,
        request: pytest.FixtureRequest,
) -> None:
    """Test connectivity to the gRPC server when domain is missing."""

    # Given a mock executor
    action_name = "test_action"
    mock_executor.run.side_effect = exception

    action_client = request.getfixturevalue(action_client_name)

    # Invoke Webhook method
    with pytest.raises(grpc.RpcError) as exc:
        action_client.Webhook(
            grpc_webhook_request,
            metadata=grpc_metadata,
            timeout=5,
            wait_for_ready=True,
        )

    # Verify the response is a gRPC error
    assert exc.value.code() == grpc.StatusCode.NOT_FOUND

    # Verify the error details
    resource_not_found = ResourceNotFound.model_validate_json(exc.value.details())
    assert resource_not_found.action_name == action_name
    assert resource_not_found.resource_type == resource_type
    assert resource_not_found.message == exception.message


@pytest.fixture
def grpc_healthcheck_client(grpc_channel: grpc.Channel) -> HealthStub:
    """Create a gRPC client for the action server."""
    client = HealthStub(grpc_channel)

    return client


@pytest.fixture
def grpc_tls_healthcheck_client(grpc_tls_channel: grpc.Channel) -> HealthStub:
    """Create a gRPC client for the action server."""
    client = HealthStub(grpc_tls_channel)

    return client


@pytest.mark.usefixtures("grpc_action_server", "grpc_tls_action_server")
@pytest.mark.parametrize("health_client_name",
                         ["grpc_healthcheck_client", "grpc_tls_healthcheck_client"])
def test_grpc_server_healthcheck(
    health_client_name,
    request: pytest.FixtureRequest,
) -> None:
    """Test healthcheck endpoint of the gRPC server."""
    health_client = request.getfixturevalue(health_client_name)

    response = health_client.Check(
        health_pb2.HealthCheckRequest(service=GRPC_ACTION_SERVER_NAME),
        wait_for_ready=True,
        timeout=5,
    )
    assert response.status == health_pb2.HealthCheckResponse.SERVING
