import asyncio
from typing import Any, AsyncIterator, Callable, Dict, List, Union, Optional
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
    ctx = MagicMock(spec=grpc.aio.ServicerContext)
    # cancelled() must return False (RPC still active) so happy-path tests do
    # not accidentally trigger the barge-in path.  MagicMock would otherwise
    # return a truthy Mock object, which would look like a cancellation.
    ctx.cancelled = MagicMock(return_value=False)
    return ctx


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
        action_call: Dict,
        sink: Optional[asyncio.Queue] = None,
        **kwargs: Any,
    ) -> ActionExecutorRunResult:
        if sink is not None:
            for event in chunk_events:
                await sink.put(event)
            await sink.put({"event": "stream_done", "result": result})
        return result

    return _run


def _make_error_run(exception: Exception) -> Callable:
    """Return an async side effect for ``executor.run`` that raises *exception*.

    Mirrors the real ``executor.run()`` contract: place ``stream_error`` in the
    sink *before* re-raising so the consumer loop always receives a terminal
    event (matching the behaviour introduced when the try-block was expanded to
    cover pre-action setup errors).
    """

    async def _run(
        action_call: Dict,
        sink: Optional[asyncio.Queue] = None,
        **kwargs: Any,
    ) -> None:
        if sink is not None:
            await sink.put({"event": "stream_error", "exception": exception})
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
    """chunk_start, chunk(s), and chunk_end within one stream sequence
    share the same response_id."""
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
    assert len(ids) == 1  # all events in one sequence share the same response_id
    assert ids.pop() != ""  # and it is non-empty


async def test_webhook_stream_each_stream_start_gets_a_distinct_response_id(
    grpc_action_server_webhook: GRPCActionServerWebhook,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    mock_executor: AsyncMock,
    mock_grpc_service_context: MagicMock,
    executor_response: ActionExecutorRunResult,
) -> None:
    """When stream_start() is called twice (e.g. to reset the accumulator), each
    resulting chunk_start must carry a different response_id so the consumer can
    distinguish the two sequences."""
    mock_grpc_service_context.invocation_metadata.return_value = []
    mock_executor.run.side_effect = _make_streaming_run(
        chunk_events=[
            {"event": "stream_start"},
            {"event": "stream_chunk", "text": "first"},
            {"event": "stream_end"},
            {"event": "stream_start"},
            {"event": "stream_chunk", "text": "second"},
            {"event": "stream_end"},
        ],
        result=executor_response,
    )

    events = await _collect_stream(
        grpc_action_server_webhook.WebhookStream(
            grpc_webhook_request, mock_grpc_service_context
        )
    )

    starts = [e for e in events if e.WhichOneof("event") == "chunk_start"]
    assert len(starts) == 2
    id_first = starts[0].chunk_start.response_id
    id_second = starts[1].chunk_start.response_id
    assert id_first != ""
    assert id_second != ""
    assert id_first != id_second  # each stream_start produces a fresh response_id

    # chunks within each sequence carry their sequence's id
    chunks = [e for e in events if e.WhichOneof("event") == "chunk"]
    assert chunks[0].chunk.response_id == id_first
    assert chunks[1].chunk.response_id == id_second


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


# ---------------------------------------------------------------------------
# WebhookStream — barge-in / AckStreamChunks
# ---------------------------------------------------------------------------


async def test_ack_stream_chunks_cancels_dispatcher(
    grpc_action_server_webhook: GRPCActionServerWebhook,
    mock_grpc_service_context: MagicMock,
) -> None:
    """AckStreamChunks must look up the dispatcher by response_id and set the
    cancelled flag so subsequent stream_chunk() calls are a no-op."""
    from rasa_sdk.executor import CollectingDispatcher
    from rasa_sdk.grpc_py import action_webhook_pb2

    dispatcher = CollectingDispatcher()
    response_id = "test-response-id"
    grpc_action_server_webhook._dispatcher_registry[response_id] = dispatcher

    ack = action_webhook_pb2.StreamChunkAck(response_id=response_id)
    await grpc_action_server_webhook.AckStreamChunks(ack, mock_grpc_service_context)

    assert dispatcher.is_streaming_cancelled


async def test_ack_stream_chunks_unknown_response_id_logs_warning(
    grpc_action_server_webhook: GRPCActionServerWebhook,
    mock_grpc_service_context: MagicMock,
    caplog: Any,
) -> None:
    """AckStreamChunks with an unknown response_id must log a warning and
    return Empty without raising."""
    import logging
    from rasa_sdk.grpc_py import action_webhook_pb2

    ack = action_webhook_pb2.StreamChunkAck(response_id="unknown-id")
    with caplog.at_level(logging.WARNING, logger="rasa_sdk.grpc_server"):
        result = await grpc_action_server_webhook.AckStreamChunks(
            ack, mock_grpc_service_context
        )

    assert result is not None  # Empty proto
    assert any("unknown-id" in r.message for r in caplog.records)


async def test_webhook_stream_barge_in_yields_final_result_after_cancel(
    grpc_action_server_webhook: GRPCActionServerWebhook,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    mock_executor: AsyncMock,
    mock_grpc_service_context: MagicMock,
    executor_response: ActionExecutorRunResult,
) -> None:
    """Barge-in: WebhookStream yields the delivered chunk, skips the cancelled
    chunk, and emits final_result (events only) after draining.

    Timeline:
      1. stream_start             → ChunkStart yielded to client
      2. stream_chunk "delivered" → Chunk yielded; no cancellation yet
      3. asyncio.sleep(0)         → event loop runs; consumer blocks on empty queue
      4. AckStreamChunks (sim)    → dispatcher cancelled
      5. stream_chunk "cancelled" → action respects _stream_cancelled, skips enqueue
      6. stream_end               → pre-yield guard fires; cancellation detected → drain
      7. stream_done              → drained; final_result yielded; loop ends

    Note: ChunkEnd is NOT yielded because the pre-yield cancellation guard
    intercepts stream_end before it is forwarded.  final_result is the terminal
    signal; ChunkEnd would be redundant after a barge-in.
    """

    async def _barge_in_run(
        action_call: Dict,
        sink: Optional[asyncio.Queue] = None,
        dispatcher: Any = None,
        **kwargs: Any,
    ) -> ActionExecutorRunResult:
        """Simulates an action that sends two chunks;
        barge-in cancels after the first."""
        if sink is not None and dispatcher is not None:
            await sink.put({"event": "stream_start"})
            await sink.put({"event": "stream_chunk", "text": "delivered"})

            # Yield to the event loop so the consumer processes stream_start and
            # stream_chunk("delivered"), then blocks on an empty queue.
            await asyncio.sleep(0)

            # Simulate AckStreamChunks arriving: cancel the stream.
            dispatcher.cancel_stream()

            # Real CollectingDispatcher.stream_chunk() checks _stream_cancelled and
            # returns early without enqueuing. Replicate that here.
            if not dispatcher.is_streaming_cancelled:  # pragma: no cover
                await sink.put({"event": "stream_chunk", "text": "cancelled"})

            await sink.put({"event": "stream_end"})
            await sink.put({"event": "stream_done", "result": executor_response})
        return executor_response

    mock_grpc_service_context.invocation_metadata.return_value = []
    mock_executor.run.side_effect = _barge_in_run

    events = await _collect_stream(
        grpc_action_server_webhook.WebhookStream(
            grpc_webhook_request, mock_grpc_service_context
        )
    )

    # ── Event sequence ──────────────────────────────────────────────────────
    event_types = [e.WhichOneof("event") for e in events]
    assert event_types == [
        "chunk_start",
        "chunk",
        "final_result",
    ], f"Unexpected event sequence: {event_types}"

    # ── Consistent response_id across streaming events ───────────────────────
    response_id = events[0].chunk_start.response_id
    assert response_id, "response_id must be non-empty"
    assert events[1].chunk.response_id == response_id

    # ── Delivered chunk carries the expected text ────────────────────────────
    assert events[1].chunk.text == "delivered"

    # ── Cancelled chunk was never enqueued and must be absent ───────────────
    chunk_texts = [e.chunk.text for e in events if e.WhichOneof("event") == "chunk"]
    assert "cancelled" not in chunk_texts

    # ── final_result carries Rasa events but no responses ───────────────────
    assert events[2].WhichOneof("event") != "error"
    final = events[2].final_result
    assert len(final.events) == len(executor_response.events)
    assert (
        MessageToDict(final.events[0])["event"] == executor_response.events[0]["event"]
    )


async def test_webhook_stream_context_cancel_breaks_promptly_without_final_result(
    grpc_action_server_webhook: GRPCActionServerWebhook,
    grpc_webhook_request: action_webhook_pb2.WebhookRequest,
    mock_executor: AsyncMock,
    mock_grpc_service_context: MagicMock,
    executor_response: ActionExecutorRunResult,
) -> None:
    """When the gRPC context is cancelled (client disconnect / network drop),
    WebhookStream must break out of the consumer loop immediately, cancel
    run_task promptly, and NOT yield final_result.

    This is distinct from a barge-in (AckStreamChunks): the client is gone so
    there is no point waiting for the action to finish or delivering a result.
    """
    action_completed = False

    async def _slow_run(
        action_call: Dict,
        sink: Optional[asyncio.Queue] = None,
        dispatcher: Any = None,
        **kwargs: Any,
    ) -> ActionExecutorRunResult:
        nonlocal action_completed
        if sink is not None:
            await sink.put({"event": "stream_start"})
            await sink.put({"event": "stream_chunk", "text": "chunk"})
            await sink.put({"event": "stream_chunk", "text": "chunk_2"})
            # Simulate a long-running action; the task must be cancelled before
            # this sleep completes.
            await asyncio.sleep(10)
            action_completed = True  # must never be reached
            await sink.put({"event": "stream_done", "result": executor_response})
        return executor_response

    mock_executor.run.side_effect = _slow_run
    mock_grpc_service_context.invocation_metadata.return_value = []
    # Simulate a client disconnect that arrives while a stream_chunk is
    # already waiting in the queue:
    #   call 1 — post-yield check after ChunkStart  → False (still connected)
    #   call 2 — post-yield check on stream_chunk    → False (still connected)
    #   call 3 — pre-yield guard on stream_chunk    → True  (now disconnected)
    # With the pre-yield guard the chunk is discarded without being sent,
    # closing the race window where one extra chunk could leak post-disconnect.
    mock_grpc_service_context.cancelled = MagicMock(side_effect=[False, False, True])

    events = await _collect_stream(
        grpc_action_server_webhook.WebhookStream(
            grpc_webhook_request, mock_grpc_service_context
        )
    )

    # ChunkStart and the first Chunk are yielded before the disconnect is
    # detected; nothing after that (no final_result).
    event_types = [e.WhichOneof("event") for e in events]
    assert event_types == [
        "chunk_start",
        "chunk",
    ], f"Unexpected event sequence: {event_types}"
    assert events[1].chunk.text == "chunk"
    assert "final_result" not in event_types

    # run_task must have been cancelled, not run to completion.
    assert not action_completed, "action must be cancelled, not run to completion"
