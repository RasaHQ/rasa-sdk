import argparse
import logging
import os
import types
import zlib
import json
from typing import List, Text, Union, Optional, Any
from ssl import SSLContext

from sanic import Sanic, response
from sanic.response import HTTPResponse
from sanic.request import Request
from sanic_cors import CORS

from rasa_sdk import utils
from rasa_sdk.cli.arguments import add_endpoint_arguments
from rasa_sdk.constants import DEFAULT_SERVER_PORT
from rasa_sdk.executor import ActionExecutor
from rasa_sdk.interfaces import ActionExecutionRejection, ActionNotFoundException

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


def create_app(
    action_package_name: Union[Text, types.ModuleType],
    cors_origins: Union[Text, List[Text], None] = "*",
    auto_reload: bool = False,
) -> Sanic:
    """Create a Sanic application and return it.

    Args:
        action_package_name: Name of the package or module to load actions
            from.
        cors_origins: CORS origins to allow.
        auto_reload: When `True`, auto-reloading of actions is enabled.

    Returns:
        A new Sanic application ready to be run.
    """
    app = Sanic("rasa_sdk", configure_logging=False, register=False)

    configure_cors(app, cors_origins)

    executor = ActionExecutor()
    executor.register_package(action_package_name)

    @app.get("/health")
    async def health(_) -> HTTPResponse:
        """Ping endpoint to check if the server is running and well."""
        body = {"status": "ok"}
        return response.json(body, status=200)

    @app.post("/webhook")
    async def webhook(request: Request) -> HTTPResponse:
        """Webhook to retrieve action calls."""
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
            executor.reload()

        try:
            result = await executor.run(action_call)
        except ActionExecutionRejection as e:
            logger.debug(e)
            body = {"error": e.message, "action_name": e.action_name}
            return response.json(body, status=400)
        except ActionNotFoundException as e:
            logger.error(e)
            body = {"error": e.message, "action_name": e.action_name}
            return response.json(body, status=404)

        return response.json(result, status=200)

    @app.get("/actions")
    async def actions(_) -> HTTPResponse:
        """List all registered actions."""
        if auto_reload:
            executor.reload()

        body = [{"name": k} for k in executor.actions.keys()]
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
    action_package_name: Union[Text, types.ModuleType],
    port: int = DEFAULT_SERVER_PORT,
    cors_origins: Union[Text, List[Text], None] = "*",
    ssl_certificate: Optional[Text] = None,
    ssl_keyfile: Optional[Text] = None,
    ssl_password: Optional[Text] = None,
    auto_reload: bool = False,
) -> None:
    """Starts the action endpoint server with given config values."""
    logger.info("Starting action endpoint server...")
    app = create_app(
        action_package_name, cors_origins=cors_origins, auto_reload=auto_reload
    )
    ssl_context = create_ssl_context(ssl_certificate, ssl_keyfile, ssl_password)
    protocol = "https" if ssl_context else "http"
    host = os.environ.get("SANIC_HOST", "0.0.0.0")

    logger.info(f"Action endpoint is up and running on {protocol}://{host}:{port}")
    app.run(host, port, ssl=ssl_context, workers=utils.number_of_sanic_workers())


if __name__ == "__main__":
    import rasa_sdk.__main__

    rasa_sdk.__main__.main()
