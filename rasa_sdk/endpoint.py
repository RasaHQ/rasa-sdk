import argparse
import logging
import types
from typing import List, Text, Union, Optional, Any
from ssl import SSLContext

from sanic import Sanic
from sanic.response import json, HTTPResponse
from sanic_cors import CORS

from rasa_sdk import utils
from rasa_sdk.cli.arguments import add_endpoint_arguments
from rasa_sdk.constants import DEFAULT_SERVER_PORT
from rasa_sdk.executor import ActionExecutor
from rasa_sdk.interfaces import ActionExecutionRejection, ActionNotFoundRejection

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
    utils.add_logging_option_arguments(parser)
    return parser


def create_ok_response(body: Any, status: int = 200) -> HTTPResponse:
    response = json(body)
    response.status = status
    return response


def create_error_response(
    message: Text, action_name: Text, status: int = 500
) -> HTTPResponse:
    response = json({"error": message, "action_name": action_name})
    response.status = status
    return response


def create_app(
    action_package_name: Union[Text, types.ModuleType],
    cors_origins: Union[Text, List[Text], None] = "*",
) -> Sanic:
    app = Sanic(__name__, configure_logging=False)

    configure_cors(app, cors_origins)

    executor = ActionExecutor()
    executor.register_package(action_package_name)

    @app.get("/health")
    async def health(request):
        """Ping endpoint to check if the server is running and well."""
        return create_ok_response({"status": "ok"})

    @app.post("/webhook")
    async def webhook(request):
        """Webhook to retrieve action calls."""
        action_call = request.json
        utils.check_version_compatibility(action_call.get("version"))
        try:
            result = await executor.run(action_call)
        except ActionExecutionRejection as e:
            logger.error(str(e))
            return create_error_response(str(e), e.action_name, 400)
        except ActionNotFoundRejection as e:
            logger.error(str(e))
            return create_error_response(str(e), e.action_name, 404)

        return create_ok_response(result)

    @app.get("/actions")
    async def actions(request):
        """List all registered actions."""
        return create_ok_response([{"name": k} for k in executor.actions.keys()])

    return app


def run(
    action_package_name: Union[Text, types.ModuleType],
    port: int = DEFAULT_SERVER_PORT,
    cors_origins: Union[Text, List[Text], None] = "*",
    ssl_certificate: Optional[Text] = None,
    ssl_keyfile: Optional[Text] = None,
    ssl_password: Optional[Text] = None,
):
    logger.info("Starting action endpoint server...")
    app = create_app(action_package_name, cors_origins=cors_origins)
    ssl_context = create_ssl_context(ssl_certificate, ssl_keyfile, ssl_password)

    app.run("0.0.0.0", port, ssl=ssl_context, workers=utils.number_of_sanic_workers())


if __name__ == "__main__":
    import rasa_sdk.__main__

    rasa_sdk.__main__.main()
