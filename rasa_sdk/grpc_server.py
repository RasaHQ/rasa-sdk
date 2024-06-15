from __future__ import annotations

import grpc
import utils
import logging
import ssl
import types
from typing import Union, Optional, Callable
from concurrent import futures
from grpc import aio
from google.protobuf.json_format import MessageToDict, ParseDict

from rasa_sdk.constants import DEFAULT_SERVER_PORT, DEFAULT_ENDPOINTS_PATH
from rasa_sdk.executor import ActionExecutor
from rasa_sdk.grpc_errors import ResourceNotFound, ResourceNotFoundType
from rasa_sdk.grpc_py import action_webhook_pb2, action_webhook_pb2_grpc
from rasa_sdk.grpc_py.action_webhook_pb2 import WebhookRequest
from rasa_sdk.interfaces import ActionExecutionRejection, ActionNotFoundException, ActionMissingDomainException
from rasa_sdk.tracing.utils import (
    get_tracer_and_context,
    TracerProvider,
    get_tracer_provider,
)

logger = logging.getLogger(__name__)


class ActionServerWebhook(action_webhook_pb2_grpc.ActionServerWebhookServicer):
    def __init__(
        self,
        executor: ActionExecutor,
        tracer_provider: Optional[TracerProvider] = None,
    ) -> None:
        """Initializes the ActionServerWebhook.

        Args:
            tracer_provider: The tracer provider.
            executor: The action executor.
        """
        self.tracer_provider = tracer_provider
        self.executor = executor

    async def webhook(self,
                      request: WebhookRequest, context,
        ) -> action_webhook_pb2.WebhookResponse:
        """Handle RPC request for the webhook.

        Args:
            request: The webhook request.
            context: The context of the request.
        """
        tracer, tracer_context, span_name = get_tracer_and_context(
            self.tracer_provider, request
        )
        with tracer.start_as_current_span(span_name, context=tracer_context) as span:
            utils.check_version_compatibility(request.version)
            try:
                action_call = MessageToDict(request, preserving_proto_field_name=True)
                result = await self.executor.run(action_call)
            except ActionExecutionRejection as e:
                logger.debug(e)
                body = {"error": e.message, "action_name": e.action_name}
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(body))
                return action_webhook_pb2.WebhookResponse()
            except ActionNotFoundException as e:
                logger.error(e)
                resource_not_found = ResourceNotFound(
                    action_name=e.action_name,
                    message=e.message,
                    resource_type=ResourceNotFoundType.ACTION,
                )
                body = resource_not_found.json()
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(body)
                return action_webhook_pb2.WebhookResponse()
            except ActionMissingDomainException as e:
                logger.error(e)
                resource_not_found = ResourceNotFound(
                    action_name=e.action_name,
                    message=e.message,
                    resource_type=ResourceNotFoundType.DOMAIN,
                )
                body = resource_not_found.json()
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(body)
                return action_webhook_pb2.WebhookResponse()
            if not result:
                return action_webhook_pb2.WebhookResponse()
            # set_span_attributes(span, request)
            response = action_webhook_pb2.WebhookResponse()

            return ParseDict(result, response)


def get_ssl_password_callback(ssl_password: str) -> Callable[[], bytes]:
    """Return a password callback function for the SSL key file.

    Args:
        ssl_password: Password for the SSL key file.

    Returns:
        A password callback function.
    """
    def password_callback() -> bytes:
        """Return the SSL password as bytes."""
        return ssl_password.encode() if ssl_password else None

    return password_callback


async def run_grpc(
    action_package_name: Union[str, types.ModuleType],
    port: int = DEFAULT_SERVER_PORT,
    ssl_certificate: Optional[str] = None,
    ssl_keyfile: Optional[str] = None,
    ssl_password: Optional[str] = None,
    endpoints: str = DEFAULT_ENDPOINTS_PATH,
):
    """Start a gRPC server to handle incoming action requests.

    Args:
        action_package_name: Name of the package which contains the custom actions.
        port: Port to start the server on.
        ssl_certificate: File path to the SSL certificate.
        ssl_keyfile: File path to the SSL key file.
        ssl_password: Password for the SSL key file.
        endpoints: Path to the endpoints file.
    """
    workers = utils.number_of_sanic_workers()
    server = aio.server(futures.ThreadPoolExecutor(max_workers=workers))
    executor = ActionExecutor()
    executor.register_package(action_package_name)
    # tracer_provider = get_tracer_provider(endpoints)
    tracer_provider = None
    action_webhook_pb2_grpc.add_ActionServerWebhookServicer_to_server(
        ActionServerWebhook(executor, tracer_provider), server
    )
    if ssl_certificate and ssl_keyfile:
        # Use SSL/TLS if certificate and key are provided
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(
            ssl_certificate,
            keyfile=ssl_keyfile,
            password=get_ssl_password_callback(ssl_password),
        )
        logger.info(
            f"Starting gRPC server with SSL support on port {port}"
        )
        server.add_secure_port(
            f"[::]:{port}", server_credentials=grpc.ssl_server_credentials(ssl_context)
        )
    else:
        logger.info(
            f"Starting gRPC server without SSL on port {port}"
        )
        # Use insecure connection if no SSL/TLS information is provided
        server.add_insecure_port(f"[::]:{port}")

    await server.start()
    logger.info(f"gRPC Server started on port {port}")
    await server.wait_for_termination()
