import pytest
from typing import Text

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from rasa_sdk.executor import ActionExecutor
from rasa_sdk.types import ActionCall


@pytest.fixture(scope="session")
def tracer_provider() -> TracerProvider:
    return TracerProvider()


@pytest.fixture(scope="session")
def span_exporter(tracer_provider: TracerProvider) -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()  # type: ignore
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


@pytest.fixture(scope="function")
def previous_num_captured_spans(span_exporter: InMemorySpanExporter) -> int:
    captured_spans = span_exporter.get_finished_spans()  # type: ignore
    return len(captured_spans)


class MockActionExecutor(ActionExecutor):
    def __init__(self) -> None:
        self.fail_if_undefined("run")

    def fail_if_undefined(self, method_name: Text) -> None:
        if not (
            hasattr(self.__class__.__base__, method_name)
            and callable(getattr(self.__class__.__base__, method_name))
        ):
            pytest.fail(
                f"method '{method_name}' not found in {self.__class__.__base__}. "
                f"This likely means the method was renamed, which means the "
                f"instrumentation needs to be adapted!"
            )

    async def run(self, action_call: ActionCall) -> None:
        pass
