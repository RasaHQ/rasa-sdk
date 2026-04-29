import asyncio
from typing import AsyncIterator, Callable, Dict, List, Union, Optional
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
from rasa_sdk.grpc_py import action_webhook_pb2
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


# ---------------------------------------------------------------------------
# Helpers for WebhookStream tests
# ---------------------------------------------------------------------------


def _make_streaming_run(
    chunk_events: List[Dict],
    result: ActionExecutorRunResult,
) -> Callable:
    """Return an async side effect for `executor.run` that populates the sink."""

    async def _run(
        action_call: Dict, sink: Optional[asyncio.Queue] = None
    ) -> ActionExecutorRunResult:
        if sink is not None:
            for event in chunk_events:
                await sink.put(event)
            await sink.put({"event": "stream_done", "result": result})
        return result

    return _run


def _make_error_run(exception: Exception) -> Callable:
    """Return an async side effect for `executor.run` that raises *exception*."""

    async def _run(action_call: Dict, sink: Optional[asyncio.Queue] = None) -> None:
        raise exception

    return _run


async def _collect_stream(
    gen: AsyncIterator,
) -> List[action_webhook_pb2.WebhookStreamEvent]:
    return [event async for event in gen]


# ---------------------------------------------------------------------------
# WebhookStream — happy path
# ---------------------------------------------------------------------------


async def test_webhook_stream_yields_chunk_start_chunks_chunk_end_final_result(
    grpc_action_server_webhook: GRPCActionServerWebhook,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    mock_executor: AsyncMock,
    mock_grpc_service_context: MagicMock,
    executor_response: ActionExecutorRunResult,
) -> None:
    """Full happy-path: stream_start → stream_chunk(s) → stream_end → final_result."""
    mock_grpc_service_context.invocation_metadata.return_value = []
    mock_executor.run.side_effect = _make_streaming_run(
        chunk_events=[
            {"event": "stream_start"},
            {"event": "stream_chunk", "text": "Hello "},
            {"event": "stream_chunk", "text": "world"},
            {"event": "stream_end"},
        ],
        result=executor_response,
    )

    events = await _collect_stream(
        grpc_action_server_webhook.WebhookStream(
            grpc_webhook_request, mock_grpc_service_context
        )
    )

    event_types = [e.WhichOneof("event") for e in events]
    assert event_types == ["chunk_start", "chunk", "chunk", "chunk_end", "final_result"]

    assert events[1].chunk.text == "Hello "
    assert events[2].chunk.text == "world"

    mock_grpc_service_context.set_code.assert_not_called()
    mock_grpc_service_context.set_details.assert_not_called()


async def test_webhook_stream_final_result_carries_events_and_responses(
    grpc_action_server_webhook: GRPCActionServerWebhook,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    mock_executor: AsyncMock,
    mock_grpc_service_context: MagicMock,
    executor_response: ActionExecutorRunResult,
    expected_grpc_webhook_response: action_webhook_pb2.WebhookResponse,
) -> None:
    mock_grpc_service_context.invocation_metadata.return_value = []
    mock_executor.run.side_effect = _make_streaming_run(
        chunk_events=[
            {"event": "stream_start"},
            {"event": "stream_end"},
        ],
        result=executor_response,
    )

    events = await _collect_stream(
        grpc_action_server_webhook.WebhookStream(
            grpc_webhook_request, mock_grpc_service_context
        )
    )

    final = next(e for e in events if e.WhichOneof("event") == "final_result")
    assert final.final_result == expected_grpc_webhook_response


async def test_webhook_stream_response_id_is_consistent_across_chunks(
    grpc_action_server_webhook: GRPCActionServerWebhook,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    mock_executor: AsyncMock,
    mock_grpc_service_context: MagicMock,
    executor_response: ActionExecutorRunResult,
) -> None:
    """All chunk messages for a single action call share the same response_id."""
    mock_grpc_service_context.invocation_metadata.return_value = []
    mock_executor.run.side_effect = _make_streaming_run(
        chunk_events=[
            {"event": "stream_start"},
            {"event": "stream_chunk", "text": "A"},
            {"event": "stream_chunk", "text": "B"},
            {"event": "stream_end"},
        ],
        result=executor_response,
    )

    events = await _collect_stream(
        grpc_action_server_webhook.WebhookStream(
            grpc_webhook_request, mock_grpc_service_context
        )
    )

    ids = {
        e.chunk_start.response_id
        if e.WhichOneof("event") == "chunk_start"
        else e.chunk.response_id
        if e.WhichOneof("event") == "chunk"
        else e.chunk_end.response_id
        for e in events
        if e.WhichOneof("event") in ("chunk_start", "chunk", "chunk_end")
    }
    assert len(ids) == 1  # all chunks share the same response_id
    assert ids.pop() != ""  # and it is non-empty


# ---------------------------------------------------------------------------
# WebhookStream — rich chunk fields mapped to proto
# ---------------------------------------------------------------------------


async def test_webhook_stream_rich_chunk_maps_all_fields_to_proto(
    grpc_action_server_webhook: GRPCActionServerWebhook,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    mock_executor: AsyncMock,
    mock_grpc_service_context: MagicMock,
    executor_response: ActionExecutorRunResult,
) -> None:
    mock_grpc_service_context.invocation_metadata.return_value = []
    mock_executor.run.side_effect = _make_streaming_run(
        chunk_events=[
            {"event": "stream_start"},
            {
                "event": "stream_chunk",
                "text": "Choose:",
                "image": "https://example.com/img.png",
                "buttons": [{"title": "Yes", "payload": "/yes"}],
                "attachment": "https://example.com/file.pdf",
            },
            {"event": "stream_end"},
        ],
        result=executor_response,
    )

    events = await _collect_stream(
        grpc_action_server_webhook.WebhookStream(
            grpc_webhook_request, mock_grpc_service_context
        )
    )

    chunk = next(e for e in events if e.WhichOneof("event") == "chunk").chunk
    assert chunk.text == "Choose:"
    assert chunk.image == "https://example.com/img.png"
    assert chunk.attachment == "https://example.com/file.pdf"
    assert len(chunk.buttons) == 1


# ---------------------------------------------------------------------------
# WebhookStream — error handling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exception, expected_status_code, expected_body_factory",
    [
        (
            ActionExecutionRejection("action_listen", "rejected"),
            grpc.StatusCode.INTERNAL,
            lambda: ActionExecutionFailed(
                action_name="action_listen", message="rejected"
            ).model_dump_json(),
        ),
        (
            ActionNotFoundException("action_listen", "not found"),
            grpc.StatusCode.NOT_FOUND,
            lambda: ResourceNotFound(
                action_name="action_listen",
                message="not found",
                resource_type=ResourceNotFoundType.ACTION,
            ).model_dump_json(),
        ),
        (
            ActionMissingDomainException("action_listen", "no domain"),
            grpc.StatusCode.NOT_FOUND,
            lambda: ResourceNotFound(
                action_name="action_listen",
                message="no domain",
                resource_type=ResourceNotFoundType.DOMAIN,
            ).model_dump_json(),
        ),
    ],
)
async def test_webhook_stream_errors_yield_stream_error_and_set_grpc_status(
    exception: Exception,
    expected_status_code: grpc.StatusCode,
    expected_body_factory: Callable,
    grpc_action_server_webhook: GRPCActionServerWebhook,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    mock_executor: AsyncMock,
    mock_grpc_service_context: MagicMock,
) -> None:
    mock_grpc_service_context.invocation_metadata.return_value = []
    mock_executor.run.side_effect = _make_error_run(exception)

    events = await _collect_stream(
        grpc_action_server_webhook.WebhookStream(
            grpc_webhook_request, mock_grpc_service_context
        )
    )

    assert len(events) == 1
    assert events[0].WhichOneof("event") == "error"
    assert events[0].error.action_name == "action_listen"

    mock_grpc_service_context.set_code.assert_called_once_with(expected_status_code)
    mock_grpc_service_context.set_details.assert_called_once_with(
        expected_body_factory()
    )


# ---------------------------------------------------------------------------
# WebhookStream — terminal-event guarantee (hang prevention)
# ---------------------------------------------------------------------------


async def test_webhook_stream_does_not_hang_when_run_returns_none(
    grpc_action_server_webhook: GRPCActionServerWebhook,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    mock_executor: AsyncMock,
    mock_grpc_service_context: MagicMock,
) -> None:
    """Stream must terminate even when executor.run() returns None.

    This happens when ``next_action`` is absent: ``executor.run()`` returns
    ``None`` without placing ``stream_done`` into the sink.  ``_run()`` must
    detect the ``None`` return value and place the terminal event itself.
    """
    mock_grpc_service_context.invocation_metadata.return_value = []
    mock_executor.run.return_value = None  # executor returns None, places nothing

    events = await _collect_stream(
        grpc_action_server_webhook.WebhookStream(
            grpc_webhook_request, mock_grpc_service_context
        )
    )

    # stream_done(result=None) → consumer breaks without yielding any event.
    # If no terminal event were placed the test would hang here, so returning
    # an empty list *proves* stream_done was received and processed.
    assert events == []
    # No error path was taken.
    mock_grpc_service_context.set_code.assert_not_called()


async def test_webhook_stream_does_not_hang_on_unexpected_exception(
    grpc_action_server_webhook: GRPCActionServerWebhook,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    mock_executor: AsyncMock,
    mock_grpc_service_context: MagicMock,
) -> None:
    """Stream must terminate when executor.run() raises an unexpected exception.

    Any ``Exception`` not in the known action-error set must be caught by
    ``_run()``, forwarded as a ``stream_error`` event, and result in a single
    ``error`` proto event and a ``INTERNAL`` gRPC status — not a hung consumer.
    """
    mock_grpc_service_context.invocation_metadata.return_value = []
    boom = RuntimeError("unexpected failure")
    mock_executor.run.side_effect = _make_error_run(boom)

    events = await _collect_stream(
        grpc_action_server_webhook.WebhookStream(
            grpc_webhook_request, mock_grpc_service_context
        )
    )

    assert len(events) == 1
    assert events[0].WhichOneof("event") == "error"
    assert "unexpected failure" in events[0].error.message

    mock_grpc_service_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
    mock_grpc_service_context.set_details.assert_called_once_with(str(boom))
