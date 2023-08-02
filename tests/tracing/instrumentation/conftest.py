import pytest

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


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
