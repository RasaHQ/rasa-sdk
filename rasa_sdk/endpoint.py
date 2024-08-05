import argparse
import logging
import os
import warnings
import zlib
import json
from functools import partial
from typing import List, Text, Union, Optional, Any
from ssl import SSLContext

from multidict import MultiDict
from sanic import Sanic, response
from sanic.compat import Header
from sanic.response import HTTPResponse
from sanic.worker.loader import AppLoader

# catching:
# - all `pkg_resources` deprecation warning from multiple dependencies
# - google rcp warnings (`pkg_resources.namespaces`)
# - open telemetry (`pkg_resources`)
# - sanic-cors (`distutils Version classes...`)
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore", category=DeprecationWarning, message=".*pkg_resources.*"
    )
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message="distutils Version classes are deprecated",
    )
    from sanic_cors import CORS
    from sanic.request import Request
    from rasa_sdk import utils
    from rasa_sdk.cli.arguments import add_endpoint_arguments
    from rasa_sdk.constants import (
        DEFAULT_ENDPOINTS_PATH,
        DEFAULT_KEEP_ALIVE_TIMEOUT,
        DEFAULT_SERVER_PORT,
    )
    from rasa_sdk.executor import ActionExecutor
    from rasa_sdk.interfaces import (
        ActionExecutionRejection,
        ActionNotFoundException,
        ActionMissingDomainException,
    )
    from rasa_sdk.plugin import plugin_manager
    from rasa_sdk.tracing.utils import (
        get_tracer_and_context,
        get_tracer_provider,
        set_span_attributes,
    )

logger = logging.getLogger(__name__)


def configure_cors(
    app: Sanic, cors_origins: Union[Text, List[Text], None] = ""
) -> None:
    """Configure CORS origins for the given app."""
    CORS(
        app, resources={r"/*": {"origins": cors_origins or ""}}, automatic_options=True
    )


def create_ssl_context(
    ssl_certificate: Optional[Text],
    ssl_keyfile: Optional[Text],
    ssl_password: Optional[Text] = None,
) -> Optional[SSLContext]:
    """Create a SSL context if a certificate is passed."""
    if ssl_certificate:
        import ssl

        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            ssl_certificate, keyfile=ssl_keyfile, password=ssl_password
        )
        return ssl_context
    else:
        return None


def create_argument_parser():
    """Parse all the command line arguments for the run script."""
    parser = argparse.ArgumentParser(description="starts the action endpoint")
    add_endpoint_arguments(parser)
    utils.add_logging_level_option_arguments(parser)
    utils.add_logging_file_arguments(parser)
    return parser


async def load_tracer_provider(endpoints: str, app: Sanic):
    """Load the tracer provider into the Sanic app."""
    tracer_provider = get_tracer_provider(endpoints)
    app.ctx.tracer_provider = tracer_provider


def create_app(
    action_executor: ActionExecutor,
    cors_origins: Union[Text, List[Text], None] = "*",
    auto_reload: bool = False,
) -> Sanic:
    """Create a Sanic application and return it.

    Args:
        action_executor: The action executor to use.
        cors_origins: CORS origins to allow.
        auto_reload: When `True`, auto-reloading of actions is enabled.

    Returns:
        A new Sanic application ready to be run.
    """
    app = Sanic("rasa_sdk", configure_logging=False)

    # Reset Sanic warnings filter that allows the triggering of Sanic warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"sanic.*")

    configure_cors(app, cors_origins)

    app.ctx.tracer_provider = None

    @app.get("/health")
    async def health(_) -> HTTPResponse:
        """Ping endpoint to check if the server is running and well."""
        body = {"status": "ok"}
        return response.json(body, status=200)

    @app.post("/webhook")
    async def webhook(request: Request) -> HTTPResponse:
        """Webhook to retrieve action calls."""
        span_name = "create_app.webhook"

        def header_to_multi_dict(headers: Header) -> MultiDict:
            return MultiDict(
                [
                    (key, value)
                    for key, value in headers.items()
                    if key.lower() not in ("content-length", "content-encoding")
                ]
            )

        tracer, context = get_tracer_and_context(
            span_name=span_name,
            tracer_provider=request.app.ctx.tracer_provider,
            tracing_carrier=header_to_multi_dict(request.headers),
        )

        with tracer.start_as_current_span(span_name, context=context) as span:
            if request.headers.get("Content-Encoding") == "deflate":
                # Decompress the request data using zlib
                decompressed_data = zlib.decompress(request.body)
                # Load the JSON data from the decompressed request data
                action_call = json.loads(decompressed_data)
            else:
                action_call = request.json
            if action_call is None:
                body = {"error": "Invalid body request"}
                return response.json(body, status=400)

            utils.check_version_compatibility(action_call.get("version"))

            if auto_reload:
                action_executor.reload()
            try:
                result = await action_executor.run(action_call)
            except ActionExecutionRejection as e:
                logger.debug(e)
                body = {"error": e.message, "action_name": e.action_name}
                return response.json(body, status=400)
            except ActionNotFoundException as e:
                logger.error(e)
                body = {"error": e.message, "action_name": e.action_name}
                return response.json(body, status=404)
            except ActionMissingDomainException as e:
                logger.debug(e)
                body = {"error": e.message, "action_name": e.action_name}
                return response.json(body, status=449)

            set_http_span_attributes(
                span,
                action_call,
                http_method="POST",
                route="/webhook",
            )

            return response.json(
                result.model_dump() if result else None,
                status=200,
            )

    @app.get("/actions")
    async def actions(_) -> HTTPResponse:
        """List all registered actions."""
        if auto_reload:
            action_executor.reload()

        body = [
            action_name_item.model_dump()
            for action_name_item in action_executor.list_actions()
        ]
        return response.json(body, status=200)

    @app.exception(Exception)
    async def exception_handler(request, exception: Exception):
        logger.error(
            msg=f"Exception occurred during execution of request {request}",
            exc_info=exception,
        )
        body = {"error": str(exception), "request_body": request.json}
        return response.json(body, status=500)

    return app


def run(
    action_executor: ActionExecutor,
    port: int = DEFAULT_SERVER_PORT,
    cors_origins: Union[Text, List[Text], None] = "*",
    ssl_certificate: Optional[Text] = None,
    ssl_keyfile: Optional[Text] = None,
    ssl_password: Optional[Text] = None,
    auto_reload: bool = False,
    endpoints: str = DEFAULT_ENDPOINTS_PATH,
    keep_alive_timeout: int = DEFAULT_KEEP_ALIVE_TIMEOUT,
) -> None:
    """Starts the action endpoint server with given config values."""
    logger.info("Starting action endpoint server...")
    loader = AppLoader(
        factory=partial(
            create_app,
            action_executor,
            cors_origins=cors_origins,
            auto_reload=auto_reload,
        ),
    )
    app = loader.load()

    app.config.KEEP_ALIVE_TIMEOUT = keep_alive_timeout

    app.register_listener(
        partial(load_tracer_provider, endpoints),
        "before_server_start",
    )

    # Attach additional sanic extensions: listeners, middleware and routing
    logger.info("Starting plugins...")
    plugin_manager().hook.attach_sanic_app_extensions(app=app)

    ssl_context = create_ssl_context(ssl_certificate, ssl_keyfile, ssl_password)
    protocol = "https" if ssl_context else "http"
    host = os.environ.get("SANIC_HOST", "0.0.0.0")

    logger.info(f"Action endpoint is up and running on {protocol}://{host}:{port}")
    app.run(
        host=host,
        port=port,
        ssl=ssl_context,
        workers=utils.number_of_sanic_workers(),
        legacy=True,
    )


def set_http_span_attributes(
    span: Any,
    action_call: dict,
    http_method: str,
    route: str,
) -> None:
    """Sets http span attributes."""
    set_span_attributes(span, action_call)
    if span.is_recording():
        span.set_attribute("http.method", http_method)
        span.set_attribute("http.route", route)


if __name__ == "__main__":
    import rasa_sdk.__main__

    rasa_sdk.__main__.main()
