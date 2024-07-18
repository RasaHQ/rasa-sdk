from typing import List, Optional, Sequence

import pytest
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from rasa_sdk.tracing.instrumentation import instrumentation
from tests.conftest import (
    MockValidationAction,
)
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, EventType, ActionExecuted


@pytest.mark.parametrize(
    "events, expected_slots_to_validate",
    [
        ([], "[]"),
        ([ActionExecuted("my_form")], "[]"),
        (
            [SlotSet("name", "Tom"), SlotSet("address", "Berlin")],
            '["name", "address"]',
        ),
    ],
)
@pytest.mark.asyncio
async def test_validation_action_run(
    tracer_provider: TracerProvider,
    span_exporter: InMemorySpanExporter,
    previous_num_captured_spans: int,
    events: List[EventType],
    expected_slots_to_validate: str,
) -> None:
    component_class = MockValidationAction

    instrumentation.instrument(
        tracer_provider,
        validation_action_class=component_class,
    )

    mock_validation_action = component_class()
    dispatcher = CollectingDispatcher()
    tracker = Tracker.from_dict({"sender_id": "test", "events": events})

    await mock_validation_action.run(dispatcher, tracker, {})

    captured_spans: Sequence[ReadableSpan] = span_exporter.get_finished_spans()  # type: ignore

    num_captured_spans = len(captured_spans) - previous_num_captured_spans
    assert num_captured_spans == 1

    captured_span = captured_spans[-1]

    assert captured_span.name == "ValidationAction.MockValidationAction.run"

    expected_attributes = {
        "class_name": component_class.__name__,
        "sender_id": "test",
        "slots_to_validate": expected_slots_to_validate,
        "action_name": "mock_validation_action",
    }

    assert captured_span.attributes == expected_attributes


@pytest.mark.parametrize(
    "events, slots, validation_events",
    [
        ([], "[]", "[]"),
        ([ActionExecuted("my_form")], "[]", '["action"]'),
        (
            [SlotSet("name", "Tom")],
            '["name"]',
            '["slot"]',
        ),
        (
            [SlotSet("name", "Tom"), SlotSet("address", "Berlin")],
            '["name", "address"]',
            '["slot"]',
        ),
    ],
)
@pytest.mark.asyncio
async def test_validation_action_extract_validation_events(
    tracer_provider: TracerProvider,
    span_exporter: InMemorySpanExporter,
    previous_num_captured_spans: int,
    events: Optional[str],
    slots: Optional[str],
    validation_events: Optional[str],
) -> None:
    component_class = MockValidationAction

    instrumentation.instrument(
        tracer_provider,
        form_validation_action_class=component_class,
    )

    mock_form_validation_action = component_class()
    dispatcher = CollectingDispatcher()
    tracker = Tracker.from_dict({"sender_id": "test", "events": events})

    await mock_form_validation_action._extract_validation_events(
        dispatcher, tracker, {}
    )

    captured_spans: Sequence[ReadableSpan] = span_exporter.get_finished_spans()  # type: ignore

    num_captured_spans = len(captured_spans) - previous_num_captured_spans
    assert num_captured_spans == 1

    captured_span = captured_spans[-1]
    expected_span_name = (
        "ValidationAction.MockValidationAction._extract_validation_events"
    )

    assert captured_span.name == expected_span_name

    expected_attributes = {
        "validation_events": validation_events,
        "slots": slots,
    }

    assert captured_span.attributes == expected_attributes
