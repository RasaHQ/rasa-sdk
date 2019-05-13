from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from builtins import str

import argparse
import logging

from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from gevent.pywsgi import WSGIServer

from rasa_sdk.cli.arguments import add_endpoint_arguments
from rasa_sdk.constants import DEFAULT_SERVER_PORT
from rasa_sdk.executor import ActionExecutor
from rasa_sdk.interfaces import ActionExecutionRejection
import rasa_sdk

from rasa_sdk import utils

logger = logging.getLogger(__name__)


def create_argument_parser():
    """Parse all the command line arguments for the run script."""

    parser = argparse.ArgumentParser(description="starts the action endpoint")
    add_endpoint_arguments(parser)
    utils.add_logging_option_arguments(parser)
    return parser


def endpoint_app(cors_origins=None, action_package_name=None):
    app = Flask(__name__)

    if not cors_origins:
        cors_origins = []

    executor = ActionExecutor()
    executor.register_package(action_package_name)

    CORS(app, resources={r"/*": {"origins": cors_origins}})

    @app.route("/health", methods=["GET", "OPTIONS"])
    @cross_origin(origins=cors_origins)
    def health():
        """Ping endpoint to check if the server is running and well."""
        return jsonify({"status": "ok"})

    @app.route("/webhook", methods=["POST", "OPTIONS"])
    @cross_origin()
    def webhook():
        """Webhook to retrieve action calls."""
        action_call = request.json
        check_version_compatibility(action_call.get("version"))
        try:
            response = executor.run(action_call)
        except ActionExecutionRejection as e:
            logger.error(str(e))
            result = {"error": str(e), "action_name": e.action_name}
            response = jsonify(result)
            response.status_code = 400
            return response

        return jsonify(response)

    @app.route("/actions", methods=["GET", "OPTIONS"])
    @cross_origin(origins=cors_origins)
    def actions():
        """List all registered actions."""
        return jsonify([{"name": k} for k in executor.actions.keys()])

    return app


def check_version_compatibility(rasa_version):
    """Check if the version of rasa and rasa_sdk are compatible.

    The version check relies on the version string being formatted as
    'x.y.z' and compares whether the numbers x and y are the same for both
    rasa and rasa_sdk.
    Args:
        rasa_version - A string containing the version of rasa that
        is making the call to the action server.
    Raises:
        Warning - The version of rasa version unknown or not compatible with
        this version of rasa_sdk.
    """
    # Check for versions of Rasa that are too old to report their version number
    if rasa_version is None:
        logger.warning(
            "You are using an old version of rasa which might "
            "not be compatible with this version of rasa_sdk "
            "({}).\n"
            "To ensure compatibility use the same version "
            "for both, modulo the last number, i.e. using version "
            "A.B.x the numbers A and B should be identical for "
            "both rasa and rasa_sdk."
            "".format(rasa_sdk.__version__)
        )
        return

    rasa = rasa_version.split(".")[:-1]
    sdk = rasa_sdk.__version__.split(".")[:-1]

    if rasa != sdk:
        logger.warning(
            "Your versions of rasa and "
            "rasa_sdk might not be compatible. You "
            "are currently running rasa version {} "
            "and rasa_sdk version {}.\n"
            "To ensure compatibility use the same "
            "version for both, modulo the last number, "
            "i.e. using version A.B.x the numbers A and "
            "B should be identical for "
            "both rasa and rasa_sdk."
            "".format(rasa_version, rasa_sdk.__version__)
        )


def run(action_package_name, port=DEFAULT_SERVER_PORT, cors_origins="*"):
    logger.info("Starting action endpoint server...")
    edp_app = endpoint_app(
        cors_origins=cors_origins, action_package_name=action_package_name
    )

    http_server = WSGIServer(("0.0.0.0", port), edp_app)

    http_server.start()
    logger.info("Action endpoint is up and running. on {}".format(http_server.address))

    http_server.serve_forever()


if __name__ == "__main__":
    import rasa_sdk.__main__

    rasa_sdk.__main__.main()
