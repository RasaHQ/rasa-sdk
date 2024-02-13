import pytest

from typing import Any, Dict, Sequence, Text, Optional
from unittest.mock import Mock
from pytest import MonkeyPatch
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry import trace

from rasa_sdk.tracing.instrumentation import instrumentation
from tests.tracing.instrumentation.conftest import MockActionExecutor
from rasa_sdk.types import ActionCall
from rasa_sdk import Tracker
from rasa_sdk.tracing.trace_provider import TraceProvider


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


@pytest.mark.asyncio
async def test_instrument_action_executor_run_registers_tracer(
    tracer_provider: TracerProvider, monkeypatch: MonkeyPatch
) -> None:
    component_class = MockActionExecutor

    mock_tracer = trace.get_tracer(__name__)

    register_tracer_mock = Mock()
    get_tracer_mock = Mock(return_value=mock_tracer)

    monkeypatch.setattr(TraceProvider, "register_tracer", register_tracer_mock())
    monkeypatch.setattr(TraceProvider, "get_tracer", get_tracer_mock)

    instrumentation.instrument(
        tracer_provider,
        action_executor_class=component_class,
    )
    register_tracer_mock.assert_called_once()

    provider = TraceProvider()
    tracer = provider.get_tracer()

    assert tracer is not None
    assert tracer == mock_tracer
