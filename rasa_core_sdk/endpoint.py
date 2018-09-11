from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import logging

from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from gevent.pywsgi import WSGIServer

from rasa_core_sdk.executor import ActionExecutor

DEFAULT_SERVER_PORT = 5055

logger = logging.getLogger(__name__)


def create_argument_parser():
    """Parse all the command line arguments for the run script."""

    parser = argparse.ArgumentParser(
            description='starts the action endpoint')
    parser.add_argument(
            '-p', '--port',
            default=DEFAULT_SERVER_PORT,
            type=int,
            help="port to run the server at")
    parser.add_argument(
            '--cors',
            nargs='*',
            type=str,
            help="enable CORS for the passed origin. "
                 "Use * to whitelist all origins")
    parser.add_argument(
            '--actions',
            type=str,
            default=None,
            help="name of action package to be loaded"
    )

    return parser


def endpoint_app(cors_origins=None,
                 action_package_name=None
                 ):
    app = Flask(__name__)

    if not cors_origins:
        cors_origins = []

    executor = ActionExecutor()
    executor.register_package(action_package_name)

    CORS(app, resources={r"/*": {"origins": cors_origins}})

    @app.route("/health",
               methods=['GET', 'OPTIONS'])
    @cross_origin(origins=cors_origins)
    def health():
        """Ping endpoint to check if the server is running and well."""
        return jsonify({"status": "ok"})

    @app.route("/webhook",
               methods=['POST', 'OPTIONS'])
    @cross_origin()
    def webhook():
        """Webhook to retrieve action calls."""
        action_call = request.json
        response = executor.run(action_call)

        return jsonify(response)

    return app


if __name__ == '__main__':
    # Running as standalone python application
    arg_parser = create_argument_parser()
    cmdline_args = arg_parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('matplotlib').setLevel(logging.WARN)

    logger.info("Starting action endpoint server...")
    edp_app = endpoint_app(cors_origins=cmdline_args.cors,
                           action_package_name=cmdline_args.actions)

    http_server = WSGIServer(('0.0.0.0', cmdline_args.port), edp_app)

    http_server.start()
    logger.info("Action endpoint is up and running. on {}"
                "".format(http_server.address))

    http_server.serve_forever()
