from typing import Sequence

import pytest
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from rasa_sdk.tracing.instrumentation import instrumentation
from tests.tracing.instrumentation.conftest import MockActionExecutor
from rasa_sdk.types import ActionCall
from rasa_sdk import Tracker


@pytest.mark.asyncio
async def test_tracing_action_executor_run(
    tracer_provider: TracerProvider,
    span_exporter: InMemorySpanExporter,
    previous_num_captured_spans: int,
) -> None:
    component_class = MockActionExecutor

    instrumentation.instrument(
        tracer_provider,
        action_executor_class=component_class,
    )

    mock_action_executor = component_class()
    action_call = ActionCall(
        {
            "next_action": "check_balance",
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

    expected_attributes = {
        "next_action": "check_balance",
        "sender_id": "test",
    }
    assert captured_span.attributes == expected_attributes
