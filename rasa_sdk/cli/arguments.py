import argparse

from rasa_sdk.constants import DEFAULT_SERVER_PORT


def action_arg(action):
    if "/" in action:
        raise argparse.ArgumentTypeError(
            "Invalid actions format. Actions file should be a python module "
            "and passed with module notation (e.g. directory.actions)."
        )
    else:
        return action


def add_endpoint_arguments(parser):
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
