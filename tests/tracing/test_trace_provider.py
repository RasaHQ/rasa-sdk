from rasa_sdk.tracing.trace_provider import TraceProvider
from opentelemetry import trace


def test_anonymization_pipeline_provider_is_singleton() -> None:
    trace_provider_1 = TraceProvider()
    trace_provider_2 = TraceProvider()

    assert trace_provider_1 is trace_provider_2
    assert trace_provider_1.tracer is trace_provider_2.tracer


def test_trace_provider() -> None:
    trace_provider = TraceProvider()
    tracer = trace.get_tracer(__name__)
    trace_provider.register_tracer(tracer)

    assert trace_provider.tracer == tracer
    assert trace_provider.get_tracer() == tracer
