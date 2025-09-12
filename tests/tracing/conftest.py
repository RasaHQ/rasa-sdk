import pathlib
import socket
import threading
from concurrent import futures
from typing import Generator, Optional

import grpc
import opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc as trace_service
import pytest
from google.protobuf.internal.containers import RepeatedCompositeFieldContainer
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans


TRACING_TESTS_FIXTURES_DIRECTORY = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def udp_server() -> Generator[socket.socket, None, None]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("localhost", 6832))
    yield sock
    sock.close()


class CapturingTestSpanExporter(trace_service.TraceServiceServicer):
    def __init__(self) -> None:
        """Initializes the capture test span exporter."""
        self.spans: Optional[RepeatedCompositeFieldContainer[ResourceSpans]] = None

    def Export(
        self, request: ExportTraceServiceRequest, context: grpc.ServicerContext
    ) -> ExportTraceServiceResponse:
        self.spans = request.resource_spans

        return ExportTraceServiceResponse()


@pytest.fixture
def span_exporter() -> CapturingTestSpanExporter:
    return CapturingTestSpanExporter()


@pytest.fixture
def result_available_event() -> threading.Event:
    return threading.Event()


@pytest.fixture
def grpc_server(
    span_exporter: CapturingTestSpanExporter,
) -> Generator[grpc.Server, None, None]:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    trace_service.add_TraceServiceServicer_to_server(  # type: ignore
        span_exporter, server
    )

    server.add_insecure_port("[::]:4317")

    server.start()
    yield server
    server.stop(None)
