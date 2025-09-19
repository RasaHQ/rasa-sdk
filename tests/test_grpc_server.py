from typing import Union, List
from unittest.mock import MagicMock, AsyncMock

import grpc
import pytest
from google.protobuf.json_format import MessageToDict, ParseDict

from rasa_sdk import ActionExecutionRejection
from rasa_sdk.executor import ActionName, ActionExecutor, ActionExecutorRunResult
from rasa_sdk.grpc_errors import (
    ActionExecutionFailed,
    ResourceNotFound,
    ResourceNotFoundType,
)
import importlib.metadata
if importlib.metadata.version('protobuf') >= '5.0.0':
    from rasa_sdk.grpc_py.pb5 import action_webhook_pb2
else:
    from rasa_sdk.grpc_py.pb4 import action_webhook_pb2
from rasa_sdk.grpc_server import GRPCActionServerWebhook
from rasa_sdk.interfaces import ActionMissingDomainException, ActionNotFoundException


@pytest.fixture
def sender_id() -> str:
    """Return sender id."""
    return "test_sender_id"


@pytest.fixture
def action_name() -> str:
    """Return action name."""
    return "action_listen"


@pytest.fixture
def grpc_webhook_request(
    sender_id: str,
    action_name: str,
    current_rasa_version: str,
) -> action_webhook_pb2.WebhookRequest:
    """Create a webhook request."""
    return action_webhook_pb2.WebhookRequest(
        next_action=action_name,
        sender_id=sender_id,
        tracker=action_webhook_pb2.Tracker(
            sender_id=sender_id,
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
        version=current_rasa_version,
        domain_digest="",
    )


@pytest.fixture
def mock_executor() -> AsyncMock:
    """Create a mock action executor."""
    return AsyncMock(spec=ActionExecutor)


@pytest.fixture
def mock_grpc_service_context() -> MagicMock:
    """Create a mock gRPC service context."""
    return MagicMock(spec=grpc.aio.ServicerContext)


@pytest.fixture
def grpc_action_server_webhook(mock_executor: AsyncMock) -> GRPCActionServerWebhook:
    """Create a GRPCActionServerWebhook instance with a mock executor."""
    return GRPCActionServerWebhook(executor=mock_executor)


@pytest.fixture
def executor_response() -> ActionExecutorRunResult:
    """Create an executor response."""
    return ActionExecutorRunResult(
        events=[{"event": "slot", "name": "test", "value": "foo"}],
        responses=[{"utter": "Hi"}],
    )


@pytest.fixture
def expected_grpc_webhook_response(
    executor_response: ActionExecutorRunResult,
) -> action_webhook_pb2.WebhookResponse:
    """Create a gRPC webhook response."""
    result = action_webhook_pb2.WebhookResponse()
    return ParseDict(executor_response.model_dump(), result)


def action_names() -> List[ActionName]:
    """Create a list of action names."""
    return [
        ActionName(name="action_listen"),
        ActionName(name="action_restart"),
        ActionName(name="action_session_start"),
    ]


def expected_grpc_actions_response() -> action_webhook_pb2.ActionsResponse:
    """Create a gRPC actions response."""
    actions = [action.model_dump() for action in action_names()]
    result = action_webhook_pb2.ActionsResponse()
    return ParseDict(
        {
            "actions": actions,
        },
        result,
    )


@pytest.mark.parametrize(
    "auto_reload, expected_reload_call_count", [(True, 1), (False, 0)]
)
async def test_grpc_action_server_webhook_no_errors(
    auto_reload: bool,
    expected_reload_call_count: int,
    grpc_action_server_webhook: GRPCActionServerWebhook,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    mock_executor: AsyncMock,
    mock_grpc_service_context: MagicMock,
    executor_response: ActionExecutorRunResult,
    expected_grpc_webhook_response: action_webhook_pb2.WebhookResponse,
) -> None:
    """Test that the gRPC action server webhook can handle a request without errors."""
    grpc_action_server_webhook.auto_reload = auto_reload
    mock_executor.run.return_value = executor_response
    response = await grpc_action_server_webhook.Webhook(
        grpc_webhook_request,
        mock_grpc_service_context,
    )

    assert response == expected_grpc_webhook_response

    mock_grpc_service_context.set_code.assert_not_called()
    mock_grpc_service_context.set_details.assert_not_called()

    assert mock_executor.reload.call_count == expected_reload_call_count

    expected_action_call = MessageToDict(
        grpc_webhook_request,
        preserving_proto_field_name=True,
    )
    mock_executor.run.assert_called_once_with(expected_action_call)


@pytest.mark.parametrize(
    "exception, expected_status_code, expected_body",
    [
        (
            ActionExecutionRejection("action_name", "message"),
            grpc.StatusCode.INTERNAL,
            ActionExecutionFailed(
                action_name="action_name", message="message"
            ).model_dump_json(),
        ),
        (
            ActionNotFoundException("action_name", "message"),
            grpc.StatusCode.NOT_FOUND,
            ResourceNotFound(
                action_name="action_name",
                message="message",
                resource_type=ResourceNotFoundType.ACTION,
            ).model_dump_json(),
        ),
        (
            ActionMissingDomainException("action_name", "message"),
            grpc.StatusCode.NOT_FOUND,
            ResourceNotFound(
                action_name="action_name",
                message="message",
                resource_type=ResourceNotFoundType.DOMAIN,
            ).model_dump_json(),
        ),
    ],
)
async def test_grpc_action_server_webhook_action_execution_rejected(
    exception: Union[
        ActionExecutionRejection, ActionNotFoundException, ActionMissingDomainException
    ],
    expected_status_code: grpc.StatusCode,
    expected_body: str,
    grpc_action_server_webhook: GRPCActionServerWebhook,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    mock_executor: AsyncMock,
    mock_grpc_service_context: MagicMock,
) -> None:
    """Test that the gRPC action server webhook can handle a request with an action execution rejection."""  # noqa: E501
    mock_executor.run.side_effect = exception
    response = await grpc_action_server_webhook.Webhook(
        grpc_webhook_request,
        mock_grpc_service_context,
    )

    assert response == action_webhook_pb2.WebhookResponse()

    mock_grpc_service_context.set_code.assert_called_once_with(expected_status_code)
    mock_grpc_service_context.set_details.assert_called_once_with(expected_body)


@pytest.mark.parametrize(
    "given_action_names, expected_grpc_actions_response",
    [
        (
            [],
            action_webhook_pb2.ActionsResponse(),
        ),
        (
            action_names(),
            expected_grpc_actions_response(),
        ),
    ],
)
async def test_grpc_action_server_actions(
    given_action_names: List[ActionName],
    expected_grpc_actions_response: action_webhook_pb2.ActionsResponse,
    grpc_action_server_webhook: GRPCActionServerWebhook,
    mock_grpc_service_context: MagicMock,
    mock_executor: AsyncMock,
) -> None:
    """Test that the gRPC action server webhook can handle a request for actions."""
    mock_executor.list_actions.return_value = given_action_names

    response = await grpc_action_server_webhook.Actions(
        action_webhook_pb2.ActionsRequest(), mock_grpc_service_context
    )

    assert response == expected_grpc_actions_response

    mock_grpc_service_context.set_code.assert_not_called()
    mock_grpc_service_context.set_details.assert_not_called()
