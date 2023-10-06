
import grpc 

import logging
import ssl
import types
from typing import List, Text, Union, Optional
from concurrent import futures
from grpc import aio
from google.protobuf.json_format import MessageToDict, ParseDict
from rasa_sdk import utils
from rasa_sdk.proto import action_webhook_pb2
from rasa_sdk.proto import action_webhook_pb2_grpc
from rasa_sdk.constants import DEFAULT_SERVER_PORT
from rasa_sdk.executor import ActionExecutor
from rasa_sdk.interfaces import ActionExecutionRejection, ActionNotFoundException
from rasa_sdk.tracing.utils import get_tracer_and_context, set_span_attributes, TracerProvider

logger = logging.getLogger(__name__)
executor = ActionExecutor()

class ActionServerWebhook(action_webhook_pb2_grpc.ActionServerWebhookServicer):
    def __init__(
            self, 
            tracer_provider: Optional[TracerProvider] = None,
            executor: Optional[ActionExecutor] = None,
            ) -> None:
        self.tracer_provider = tracer_provider
        self.executor = executor

    async def webhook(self, request, context):
        tracer, context, span_name = get_tracer_and_context(self.tracer_provider, request)
        with tracer.start_as_current_span(span_name, context=context) as span:
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
                body = {"error": e.message, "action_name": e.action_name}
                context.set_code(grpc.StatusCode.NOTFOUND)
                context.set_details(str(body))
                return action_webhook_pb2.WebhookResponse()
            if not result:
                return action_webhook_pb2.WebhookResponse()
            #set_span_attributes(span, request)
            response = action_webhook_pb2.WebhookResponse()
            
            return ParseDict(result, response)
def get_ssl_password_callback(ssl_password):
    def password_callback(*args, **kwargs):
        return ssl_password.encode() if ssl_password else None
    return password_callback

async def run_grpc(
        action_package_name: Union[Text, types.ModuleType],
        port: int = DEFAULT_SERVER_PORT,
        tracer_provider: Optional[TracerProvider] = None,
        ssl_certificate: Optional[Text] = None,
        ssl_keyfile: Optional[Text] = None,
        ssl_password: Optional[Text] = None,
    ):
    workers = utils.number_of_sanic_workers()
    server = aio.server(futures.ThreadPoolExecutor(max_workers=workers))
    executor = ActionExecutor()
    executor.register_package(action_package_name)
    action_webhook_pb2_grpc.add_ActionServerWebhookServicer_to_server(
        ActionServerWebhook(tracer_provider, executor),
        server
    )
    if ssl_certificate and ssl_keyfile:
        # Use SSL/TLS if certificate and key are provided
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(ssl_certificate, keyfile=ssl_keyfile, password=get_ssl_password_callback(ssl_password))
        server.add_secure_port(f'[::]:{port}', server_credentials=grpc.ssl_server_credentials(ssl_context))
    else:
        # Use insecure connection if no SSL/TLS information is provided
        server.add_insecure_port(f'[::]:{port}')

    await server.start()
    print(f"gRPC Server started on port {port}")
    await server.wait_for_termination()

