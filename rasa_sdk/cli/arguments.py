import argparse

from rasa_sdk.constants import DEFAULT_SERVER_PORT, DEFAULT_ENDPOINTS_PATH


def action_arg(actions_module_path: str) -> str:
    """Validate the action module path.

    Valid action module path is python module, so it should not contain a slash.

    Args:
        actions_module_path: Path to the actions python module.

    Returns:
        actions_module_path: If provided module path is valid.

    Raises:
        argparse.ArgumentTypeError: If the module path is invalid.
    """
    if "/" in actions_module_path:
        raise argparse.ArgumentTypeError(
            "Invalid actions format. Actions file should be a python module "
            "and passed with module notation (e.g. directory.actions)."
        )
    else:
        return actions_module_path


def add_endpoint_arguments(parser: argparse.ArgumentParser) -> None:
    """Add all the arguments to the argument parser."""
    parser.add_argument(
        "-p",
        "--port",
        default=DEFAULT_SERVER_PORT,
        type=int,
        help="port to run the server at",
    )
    parser.add_argument(
        "--cors",
        nargs="*",
        type=str,
        help="enable CORS for the passed origin. Use * to whitelist all origins",
    )
    parser.add_argument(
        "--actions",
        type=action_arg,
        default=None,
        help="name of action package to be loaded",
    )
    parser.add_argument(
        "--actions-module",
        type=action_arg,
        default=None,
        help="name of action package to be loaded",
    )
    parser.add_argument(
        "--ssl-keyfile",
        default=None,
        help="Set the SSL certificate to create a TLS secured server.",
    )
    parser.add_argument(
        "--ssl-certificate",
        default=None,
        help="Set the SSL certificate to create a TLS secured server.",
    )
    parser.add_argument(
        "--ssl-password",
        default=None,
        help="If your ssl-keyfile is protected by a password, you can specify it "
        "using this parameter. "
        "Not supported in grpc mode.",
    )
    parser.add_argument(
        "--ssl-ca-file",
        default=None,
        help="If you want to authenticate the client using a certificate, you can "
        "specify the CA certificate of the client using this parameter. "
        "Supported only in grpc mode.",
    )
    parser.add_argument(
        "--auto-reload",
        help="Enable auto-reloading of modules containing Action subclasses.",
        action="store_true",
    )
    parser.add_argument(
        "--endpoints",
        default=DEFAULT_ENDPOINTS_PATH,
        help="Configuration file for the assistant as a yml file.",
    )
    parser.add_argument(
        "--grpc", help="Starts grpc server instead of http", action="store_true"
    )
