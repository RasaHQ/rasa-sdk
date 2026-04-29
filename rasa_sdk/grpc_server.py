from __future__ import annotations

import contextlib
import signal
import uuid

import asyncio

import grpc
import logging
from typing import AsyncIterator, Optional, Any, Dict
from concurrent import futures
from grpc import aio
from grpc_health.v1 import health
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc
from google.protobuf.json_format import MessageToDict, ParseDict
from grpc.aio import Metadata
from multidict import MultiDict

from rasa_sdk.constants import (
    DEFAULT_SERVER_PORT,
    DEFAULT_ENDPOINTS_PATH,
    NO_GRACE_PERIOD,
)
from rasa_sdk.executor import ActionExecutor
from rasa_sdk.grpc_errors import (
    ResourceNotFound,
    ResourceNotFoundType,
    ActionExecutionFailed,
)
from rasa_sdk.grpc_py import (
    action_webhook_pb2,
    action_webhook_pb2_grpc,
)
from rasa_sdk.grpc_py.action_webhook_pb2 import (
    ActionsResponse,
    ActionsRequest,
    WebhookRequest,
)
from rasa_sdk.interfaces import (
    ActionExecutionRejection,
    ActionNotFoundException,
    ActionMissingDomainException,
)
from rasa_sdk.tracing.utils import (
    get_tracer_provider,
    TracerProvider,
    get_tracer_and_context,
    set_span_attributes,
)
from rasa_sdk.utils import (
    check_version_compatibility,
    number_of_sanic_workers,
    file_as_bytes,
)

logger = logging.getLogger(__name__)


GRPC_ACTION_SERVER_NAME = "ActionServer"


def _convert_metadata_to_multidict(
    metadata: Optional[Metadata],
) -> Optional[MultiDict]:
    """Convert gRPC invocation metadata (list of 2-tuples) to a MultiDict."""
    if not metadata:
        return None
    return MultiDict(metadata)


class GRPCActionServerWebhook(action_webhook_pb2_grpc.ActionServiceServicer):
    """Runs webhook RPC which is served through gRPC server."""

    def __init__(
        self,
        executor: ActionExecutor,
        auto_reload: bool = False,
        tracer_provider: Optional[TracerProvider] = None,
    ) -> None:
        """Initializes the ActionServerWebhook.

        Args:
            tracer_provider: The tracer provider.
            auto_reload: Enable auto-reloading of modules containing Action subclasses.
            executor: The action executor.
        """
        self.tracer_provider = tracer_provider
        self.auto_reload = auto_reload
        self.executor = executor

    async def Actions(
        self,
        request: ActionsRequest,
        context: grpc.aio.ServicerContext,
    ) -> ActionsResponse:
        """Handle RPC request for the actions.

        Args:
            request: The actions request.
            context: The context of the request.

        Returns:
            gRPC response.
        """
        if self.auto_reload:
            self.executor.reload()

        actions = [action.model_dump() for action in self.executor.list_actions()]
        response = ActionsResponse()
        return ParseDict(
            {
                "actions": actions,
            },
            response,
        )

    async def Webhook(
        self,
        request: WebhookRequest,
        context: grpc.aio.ServicerContext,
    ) -> action_webhook_pb2.WebhookResponse:
        """Handle RPC request for the webhook.

        Args:
            request: The webhook request.
            context: The context of the request.

        Returns:
            gRPC response.
        """
        span_name = "GRPCActionServerWebhook.Webhook"
        invocation_metadata = context.invocation_metadata()

        tracer, tracing_context = get_tracer_and_context(
            span_name=span_name,
            tracer_provider=self.tracer_provider,
            tracing_carrier=_convert_metadata_to_multidict(invocation_metadata),
        )

        with tracer.start_as_current_span(span_name, context=tracing_context) as span:
            check_version_compatibility(request.version)
            if self.auto_reload:
                self.executor.reload()
            try:
                action_call = MessageToDict(request, preserving_proto_field_name=True)
                result = await self.executor.run(action_call)
            except ActionExecutionRejection as e:
                logger.debug(e)

                body = ActionExecutionFailed(
                    action_name=e.action_name, message=e.message
                ).model_dump_json()
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(body)
                return action_webhook_pb2.WebhookResponse()
            except ActionNotFoundException as e:
                logger.error(e)
                body = ResourceNotFound(
                    action_name=e.action_name,
                    message=e.message,
                    resource_type=ResourceNotFoundType.ACTION,
                ).model_dump_json()
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(body)
                return action_webhook_pb2.WebhookResponse()
            except ActionMissingDomainException as e:
                logger.error(e)
                body = ResourceNotFound(
                    action_name=e.action_name,
                    message=e.message,
                    resource_type=ResourceNotFoundType.DOMAIN,
                ).model_dump_json()
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(body)
                return action_webhook_pb2.WebhookResponse()
            if not result:
                return action_webhook_pb2.WebhookResponse()

            _set_grpc_span_attributes(span, action_call, method_name="Webhook")
            response = action_webhook_pb2.WebhookResponse()
            return ParseDict(result.model_dump(), response)

    async def WebhookStream(
        self,
        request: WebhookRequest,
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[action_webhook_pb2.WebhookStreamEvent]:
        """Handle streaming RPC request for the webhook.

        Runs the action and yields :class:`WebhookStreamEvent` messages to the
        client as the action produces text chunks.  The event sequence is:

        1. ``chunk_start``   — action has begun a streaming response.
        2. ``chunk``         — one or more response chunks from the action (text,
                               image, buttons, elements, attachment, or custom).
        3. ``chunk_end``     — the current streaming response is complete.
        4. ``final_result``  — the full :class:`WebhookResponse` (events +
                               non-streaming responses) after the action finishes.

        On error a single ``error`` event is yielded and the stream ends with
        the appropriate gRPC status code set on *context*.

        The ``response_id`` field on chunk messages ties together all chunks
        that belong to the same streaming response within one action execution.

        Args:
            request: The webhook request.
            context: The context of the request.

        Yields:
            :class:`WebhookStreamEvent` messages.
        """
        span_name = "GRPCActionServerWebhook.WebhookStream"
        invocation_metadata = context.invocation_metadata()

        tracer, tracing_context = get_tracer_and_context(
            span_name=span_name,
            tracer_provider=self.tracer_provider,
            tracing_carrier=_convert_metadata_to_multidict(invocation_metadata),
        )

        with tracer.start_as_current_span(span_name, context=tracing_context) as span:
            check_version_compatibility(request.version)
            if self.auto_reload:
                self.executor.reload()

            action_call = MessageToDict(request, preserving_proto_field_name=True)
            action_name = action_call.get("next_action", "")
            sink: asyncio.Queue = asyncio.Queue()

            async def _run() -> None:
                """Run the action and always place a terminal event in the sink.

                Guarantees the consumer loop receives either ``stream_done`` or
                ``stream_error`` even when ``executor.run()`` returns ``None``
                (missing ``next_action``), in which case it returns without
                placing ``stream_done``.

                All exceptions from ``executor.run()`` are suppressed here
                because ``executor.run()`` already places ``stream_error`` in
                the sink before re-raising.  Suppressing prevents the
                ``asyncio.Task`` from becoming an unhandled-exception task.
                Unexpected errors are still logged with a full traceback.
                """
                try:
                    result = await self.executor.run(action_call, sink=sink)
                    if result is None:
                        # next_action was absent; executor.run() returned without
                        # placing stream_done, so we must do it here.
                        await sink.put({"event": "stream_done", "result": None})
                except (
                    ActionExecutionRejection,
                    ActionNotFoundException,
                    ActionMissingDomainException,
                ):
                    pass  # stream_error already placed in sink by executor.run()
                except Exception:
                    logger.exception(
                        f"Unexpected error running action "
                        f"'{action_call.get('next_action')}'"
                    )
                    # stream_error already placed in sink by executor.run()

            run_task = asyncio.ensure_future(_run())

            try:
                current_response_id: str = ""
                while True:
                    chunk = await sink.get()
                    event_type = chunk.get("event")

                    if event_type == "stream_start":
                        current_response_id = uuid.uuid4().hex
                        yield action_webhook_pb2.WebhookStreamEvent(
                            chunk_start=action_webhook_pb2.ChunkStart(
                                response_id=current_response_id
                            )
                        )
                    elif event_type == "stream_chunk":
                        # Only the fields defined in the Chunk protobuf message
                        # are serialised. Any extra kwargs passed to
                        # stream_chunk() arrive in the payload dict but are
                        # intentionally dropped here because the wire format
                        # has no place for them.
                        yield action_webhook_pb2.WebhookStreamEvent(
                            chunk=ParseDict(
                                {
                                    k: chunk[k]
                                    for k in (
                                        "text",
                                        "image",
                                        "custom",
                                        "attachment",
                                        "buttons",
                                        "elements",
                                    )
                                    if k in chunk
                                },
                                action_webhook_pb2.Chunk(
                                    response_id=current_response_id
                                ),
                            )
                        )
                    elif event_type == "stream_end":
                        yield action_webhook_pb2.WebhookStreamEvent(
                            chunk_end=action_webhook_pb2.ChunkEnd(
                                response_id=current_response_id
                            )
                        )
                    elif event_type == "stream_done":
                        result = chunk.get("result")
                        if result:
                            final_response = action_webhook_pb2.WebhookResponse()
                            ParseDict(result.model_dump(), final_response)
                            yield action_webhook_pb2.WebhookStreamEvent(
                                final_result=final_response
                            )
                        _set_grpc_span_attributes(
                            span, action_call, method_name="WebhookStream"
                        )
                        break
                    elif event_type == "stream_error":
                        exc = chunk.get("exception")
                        if isinstance(exc, ActionExecutionRejection):
                            logger.debug(exc)
                            context.set_code(grpc.StatusCode.INTERNAL)
                            context.set_details(
                                ActionExecutionFailed(
                                    action_name=exc.action_name, message=exc.message
                                ).model_dump_json()
                            )
                        elif isinstance(exc, ActionNotFoundException):
                            logger.error(exc)
                            context.set_code(grpc.StatusCode.NOT_FOUND)
                            context.set_details(
                                ResourceNotFound(
                                    action_name=exc.action_name,
                                    message=exc.message,
                                    resource_type=ResourceNotFoundType.ACTION,
                                ).model_dump_json()
                            )
                        elif isinstance(exc, ActionMissingDomainException):
                            logger.error(exc)
                            context.set_code(grpc.StatusCode.NOT_FOUND)
                            context.set_details(
                                ResourceNotFound(
                                    action_name=exc.action_name,
                                    message=exc.message,
                                    resource_type=ResourceNotFoundType.DOMAIN,
                                ).model_dump_json()
                            )
                        else:
                            logger.error(exc)
                            context.set_code(grpc.StatusCode.INTERNAL)
                            context.set_details(str(exc))
                        yield action_webhook_pb2.WebhookStreamEvent(
                            error=action_webhook_pb2.StreamError(
                                action_name=action_name,
                                message=str(exc),
                            )
                        )
                        break
            finally:
                if not run_task.done():
                    run_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await run_task


def _set_grpc_span_attributes(
    span: Any, action_call: Dict[str, Any], method_name: str
) -> None:
    """Sets grpc span attributes."""
    set_span_attributes(span, action_call)
    if span.is_recording():
        span.set_attribute("grpc.method", method_name)


def _get_signal_name(signal_number: int) -> str:
    """Return the signal name for the given signal number."""
    return signal.Signals(signal_number).name


def _initialise_interrupts(server: grpc.Server) -> None:
    """Initialise handlers for kernel signal interrupts."""

    async def handle_sigint(signal_received: int):
        """Handle the received signal."""
        logger.info(
            f"Received {_get_signal_name(signal_received)} signal."
            "Stopping gRPC server..."
        )
        await server.stop(NO_GRACE_PERIOD)
        logger.info("gRPC server stopped.")

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(
        signal.SIGINT, lambda: asyncio.create_task(handle_sigint(signal.SIGINT))
    )
    loop.add_signal_handler(
        signal.SIGTERM, lambda: asyncio.create_task(handle_sigint(signal.SIGTERM))
    )


def _initialise_health_service(server: grpc.Server):
    """Initialise the health service.

    Args:
        server: The gRPC server.
    """
    health_servicer = health.HealthServicer(
        experimental_non_blocking=True,
        experimental_thread_pool=futures.ThreadPoolExecutor(max_workers=10),
    )
    health_servicer.set(GRPC_ACTION_SERVER_NAME, health_pb2.HealthCheckResponse.SERVING)
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)


def _initialise_action_service(
    server: grpc.Server,
    action_executor: ActionExecutor,
    auto_reload: bool,
    endpoints: str,
):
    """Initialise the action service.

    Args:
        server: The gRPC server.
        action_executor: The action executor.
        auto_reload: Enable auto-reloading of modules containing Action subclasses.
        endpoints: Path to the endpoints file.
    """
    tracer_provider = get_tracer_provider(endpoints)
    action_webhook_pb2_grpc.add_ActionServiceServicer_to_server(
        GRPCActionServerWebhook(action_executor, auto_reload, tracer_provider), server
    )


def _initialise_port(
    server: grpc.Server,
    port: int = DEFAULT_SERVER_PORT,
    ssl_server_cert: Optional[bytes] = None,
    ssl_server_cert_key: Optional[bytes] = None,
    ssl_ca_cert: Optional[bytes] = None,
) -> None:
    if ssl_server_cert and ssl_server_cert_key:
        # Use SSL/TLS if certificate and key are provided
        grpc.ssl_channel_credentials()
        logger.info(f"Starting gRPC server with SSL support on port {port}")
        server.add_secure_port(
            f"[::]:{port}",
            server_credentials=grpc.ssl_server_credentials(
                private_key_certificate_chain_pairs=[
                    (ssl_server_cert_key, ssl_server_cert)
                ],
                root_certificates=ssl_ca_cert,
                require_client_auth=True if ssl_ca_cert else False,
            ),
        )
    else:
        logger.info(f"Starting gRPC server without SSL on port {port}")
        # Use insecure connection if no SSL/TLS information is provided
        server.add_insecure_port(f"[::]:{port}")


def _initialise_grpc_server(
    action_executor: ActionExecutor,
    port: int = DEFAULT_SERVER_PORT,
    max_number_of_workers: int = 10,
    ssl_server_cert: Optional[bytes] = None,
    ssl_server_cert_key: Optional[bytes] = None,
    ssl_ca_cert: Optional[bytes] = None,
    auto_reload: bool = False,
    endpoints: str = DEFAULT_ENDPOINTS_PATH,
) -> grpc.Server:
    """Create a gRPC server to handle incoming action requests.

    Args:
        action_executor: The action executor.
        port: Port to start the server on.
        max_number_of_workers: Maximum number of workers to use.
        ssl_server_cert: File path to the SSL certificate.
        ssl_server_cert_key: File path to the SSL key file.
        ssl_ca_cert: File path to the SSL CA certificate file.
        auto_reload: Enable auto-reloading of modules containing Action subclasses.
        endpoints: Path to the endpoints file.

    Returns:
        The gRPC server.
    """
    server = aio.server(
        futures.ThreadPoolExecutor(max_workers=max_number_of_workers),
        compression=grpc.Compression.Gzip,
    )

    _initialise_health_service(server)
    _initialise_action_service(server, action_executor, auto_reload, endpoints)
    _initialise_port(server, port, ssl_server_cert, ssl_server_cert_key, ssl_ca_cert)

    return server


async def run_grpc(
    action_executor: ActionExecutor,
    port: int = DEFAULT_SERVER_PORT,
    ssl_server_cert_path: Optional[str] = None,
    ssl_server_cert_key_file_path: Optional[str] = None,
    ssl_ca_file_path: Optional[str] = None,
    auto_reload: bool = False,
    endpoints: str = DEFAULT_ENDPOINTS_PATH,
):
    """Start a gRPC server to handle incoming action requests.

    Args:
        action_executor: The action executor.
        port: Port to start the server on.
        ssl_server_cert_path: File path to the client SSL certificate.
        ssl_server_cert_key_file_path: File path to the SSL key for client cert.
        ssl_ca_file_path: File path to the SSL CA certificate file.
        auto_reload: Enable auto-reloading of modules containing Action subclasses.
        endpoints: Path to the endpoints file.
    """
    max_number_of_workers = number_of_sanic_workers()
    ssl_server_cert = (
        file_as_bytes(ssl_server_cert_path) if (ssl_server_cert_path) else None
    )
    ssl_server_cert_key = (
        file_as_bytes(ssl_server_cert_key_file_path)
        if (ssl_server_cert_key_file_path)
        else None
    )
    ssl_ca_cert = file_as_bytes(ssl_ca_file_path) if (ssl_ca_file_path) else None

    server = _initialise_grpc_server(
        action_executor,
        port,
        max_number_of_workers,
        ssl_server_cert,
        ssl_server_cert_key,
        ssl_ca_cert,
        auto_reload,
        endpoints,
    )

    _initialise_interrupts(server)

    await server.start()
    logger.info(f"gRPC Server started on port {port}")
    await server.wait_for_termination()
