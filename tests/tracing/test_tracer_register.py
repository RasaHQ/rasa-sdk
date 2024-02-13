from rasa_sdk.tracing.tracer_register import ActionExecutorTracerRegister
from opentelemetry import trace


def test_tracer_register_is_singleton() -> None:
    tracer_register_1 = ActionExecutorTracerRegister()
    tracer_register_2 = ActionExecutorTracerRegister()

    assert tracer_register_1 is tracer_register_2
    assert tracer_register_1.tracer is tracer_register_2.tracer


def test_trace_register() -> None:
    tracer_register = ActionExecutorTracerRegister()
    assert tracer_register.get_tracer() is None

    tracer = trace.get_tracer(__name__)
    tracer_register.register_tracer(tracer)

    assert tracer_register.tracer == tracer
    assert tracer_register.get_tracer() == tracer
