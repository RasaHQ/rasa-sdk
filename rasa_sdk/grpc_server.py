from __future__ import annotations

import signal

import asyncio

import grpc
import logging
import types
from typing import Union, Optional, Any, Dict
from concurrent import futures
from grpc import aio
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
    health_pb2_grpc,
)
from rasa_sdk.grpc_py.action_webhook_pb2 import (
    ActionsResponse,
    ActionsRequest,
    WebhookRequest,
)
from rasa_sdk.grpc_py.health_pb2 import HealthCheckRequest, HealthCheckResponse
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


class GRPCActionServerHealthCheck(health_pb2_grpc.HealthServiceServicer):
    """Runs health check RPC which is served through gRPC server."""

    def __init__(self) -> None:
        """Initializes the HealthServicer."""
        pass

    def Check(self, request: HealthCheckRequest, context) -> HealthCheckResponse:
        """Handle RPC request for the health check.

        Args:
            request: The health check request.
            context: The context of the request.

        Returns:
            gRPC response.
        """
        response = HealthCheckResponse()
        return response


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

        def convert_metadata_to_multidict(
            metadata: Optional[Metadata],
        ) -> Optional[MultiDict]:
            """Convert list of tuples to multidict."""
            if not metadata:
                return None
            return MultiDict(metadata)

        tracer, tracing_context = get_tracer_and_context(
            span_name=span_name,
            tracer_provider=self.tracer_provider,
            tracing_carrier=convert_metadata_to_multidict(invocation_metadata),
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

            set_grpc_span_attributes(span, action_call, method_name="Webhook")
            response = action_webhook_pb2.WebhookResponse()
            return ParseDict(result, response)


def set_grpc_span_attributes(
    span: Any, action_call: Dict[str, Any], method_name: str
) -> None:
    """Sets grpc span attributes."""
    set_span_attributes(span, action_call)
    if span.is_recording():
        span.set_attribute("grpc.method", method_name)


def get_signal_name(signal_number: int) -> str:
    """Return the signal name for the given signal number."""
    return signal.Signals(signal_number).name


def initialise_interrupts(server: grpc.aio.Server) -> None:
    """Initialise handlers for kernel signal interrupts."""

    async def handle_sigint(signal_received: int):
        """Handle the received signal."""
        logger.info(
            f"Received {get_signal_name(signal_received)} signal."
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


async def run_grpc(
    action_package_name: Union[str, types.ModuleType],
    port: int = DEFAULT_SERVER_PORT,
    ssl_certificate: Optional[str] = None,
    ssl_keyfile: Optional[str] = None,
    ssl_ca_file: Optional[str] = None,
    auto_reload: bool = False,
    endpoints: str = DEFAULT_ENDPOINTS_PATH,
):
    """Start a gRPC server to handle incoming action requests.

    Args:
        action_package_name: Name of the package which contains the custom actions.
        port: Port to start the server on.
        ssl_certificate: File path to the SSL certificate.
        ssl_keyfile: File path to the SSL key file.
        ssl_ca_file: File path to the SSL CA certificate file.
        auto_reload: Enable auto-reloading of modules containing Action subclasses.
        endpoints: Path to the endpoints file.
    """
    workers = number_of_sanic_workers()
    server = aio.server(
        futures.ThreadPoolExecutor(max_workers=workers),
        compression=grpc.Compression.Gzip,
    )
    initialise_interrupts(server)
    executor = ActionExecutor()
    executor.register_package(action_package_name)
    tracer_provider = get_tracer_provider(endpoints)
    action_webhook_pb2_grpc.add_ActionServiceServicer_to_server(
        GRPCActionServerWebhook(executor, auto_reload, tracer_provider), server
    )

    health_pb2_grpc.add_HealthServiceServicer_to_server(
        GRPCActionServerHealthCheck(), server
    )

    ca_cert = file_as_bytes(ssl_ca_file) if ssl_ca_file else None

    if ssl_certificate and ssl_keyfile:
        # Use SSL/TLS if certificate and key are provided
        grpc.ssl_channel_credentials()
        private_key = file_as_bytes(ssl_keyfile)
        certificate_chain = file_as_bytes(ssl_certificate)
        logger.info(f"Starting gRPC server with SSL support on port {port}")
        server.add_secure_port(
            f"[::]:{port}",
            server_credentials=grpc.ssl_server_credentials(
                private_key_certificate_chain_pairs=[(private_key, certificate_chain)],
                root_certificates=ca_cert,
                require_client_auth=True if ca_cert else False,
            ),
        )
    else:
        logger.info(f"Starting gRPC server without SSL on port {port}")
        # Use insecure connection if no SSL/TLS information is provided
        server.add_insecure_port(f"[::]:{port}")

    await server.start()
    logger.info(f"gRPC Server started on port {port}")
    await server.wait_for_termination()
