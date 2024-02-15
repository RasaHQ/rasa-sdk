import pytest

from typing import Any, Dict, Sequence, Text, Optional, List
from unittest.mock import Mock
from pytest import MonkeyPatch
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry import trace
from rasa_sdk.events import ActionExecuted, SlotSet

from rasa_sdk.tracing.instrumentation import instrumentation
from tests.tracing.instrumentation.conftest import MockActionExecutor
from rasa_sdk.types import ActionCall
from rasa_sdk import Tracker
from rasa_sdk.tracing.tracer_register import ActionExecutorTracerRegister
from rasa_sdk.executor import CollectingDispatcher


dispatcher1 = CollectingDispatcher()
dispatcher1.utter_message(template="utter_greet")
dispatcher2 = CollectingDispatcher()
dispatcher2.utter_message("Hello")
dispatcher3 = CollectingDispatcher()
dispatcher3.utter_message("Hello")
dispatcher3.utter_message(template="utter_greet")


@pytest.mark.parametrize(
    "action_name, expected",
    [
        ("check_balance", {"action_name": "check_balance", "sender_id": "test"}),
        (None, {"sender_id": "test"}),
    ],
)
@pytest.mark.asyncio
async def test_tracing_action_executor_run(
    tracer_provider: TracerProvider,
    span_exporter: InMemorySpanExporter,
    previous_num_captured_spans: int,
    action_name: Optional[str],
    expected: Dict[Text, Any],
) -> None:
    component_class = MockActionExecutor

    instrumentation.instrument(
        tracer_provider,
        action_executor_class=component_class,
    )

    mock_action_executor = component_class()
    action_call = ActionCall(
        {
            "next_action": action_name,
            "sender_id": "test",
            "tracker": Tracker("test", {}, {}, [], False, None, {}, ""),
            "version": "1.0.0",
            "domain": {},
        }
    )
    await mock_action_executor.run(action_call)

    captured_spans: Sequence[
        ReadableSpan
    ] = span_exporter.get_finished_spans()  # type: ignore

    num_captured_spans = len(captured_spans) - previous_num_captured_spans
    assert num_captured_spans == 1

    captured_span = captured_spans[-1]

    assert captured_span.name == "MockActionExecutor.run"

    assert captured_span.attributes == expected


def test_instrument_action_executor_run_registers_tracer(
    tracer_provider: TracerProvider, monkeypatch: MonkeyPatch
) -> None:
    component_class = MockActionExecutor

    mock_tracer = trace.get_tracer(__name__)

    register_tracer_mock = Mock()
    get_tracer_mock = Mock(return_value=mock_tracer)

    monkeypatch.setattr(
        ActionExecutorTracerRegister, "register_tracer", register_tracer_mock()
    )
    monkeypatch.setattr(ActionExecutorTracerRegister, "get_tracer", get_tracer_mock)

    instrumentation.instrument(
        tracer_provider,
        action_executor_class=component_class,
    )
    register_tracer_mock.assert_called_once()

    provider = ActionExecutorTracerRegister()
    tracer = provider.get_tracer()

    assert tracer is not None
    assert tracer == mock_tracer


@pytest.mark.parametrize(
    "events, messages, expected",
    [
        ([], [], {"events": "[]", "slots": "[]", "utters": "[]", "message_count": 0}),
        (
            [ActionExecuted("my_form")],
            dispatcher2.messages,
            {"events": '["action"]', "slots": "[]", "utters": "[]", "message_count": 1},
        ),
        (
            [ActionExecuted("my_form"), SlotSet("my_slot", "some_value")],
            dispatcher1.messages,
            {
                "events": '["action", "slot"]',
                "slots": '["my_slot"]',
                "utters": '["utter_greet"]',
                "message_count": 1,
            },
        ),
        (
            [SlotSet("my_slot", "some_value")],
            dispatcher3.messages,
            {
                "events": '["slot"]',
                "slots": '["my_slot"]',
                "utters": '["utter_greet"]',
                "message_count": 2,
            },
        ),
    ],
)
def test_tracing_action_executor_create_api_response(
    tracer_provider: TracerProvider,
    span_exporter: InMemorySpanExporter,
    previous_num_captured_spans: int,
    events: Optional[List],
    messages: Optional[List],
    expected: Dict[Text, Any],
) -> None:
    component_class = MockActionExecutor

    instrumentation.instrument(
        tracer_provider,
        action_executor_class=component_class,
    )

    mock_action_executor = component_class()

    mock_action_executor._create_api_response(events, messages)

    captured_spans: Sequence[
        ReadableSpan
    ] = span_exporter.get_finished_spans()  # type: ignore

    num_captured_spans = len(captured_spans) - previous_num_captured_spans
    assert num_captured_spans == 1

    captured_span = captured_spans[-1]

    assert captured_span.name == "MockActionExecutor._create_api_response"

    assert captured_span.attributes == expected
