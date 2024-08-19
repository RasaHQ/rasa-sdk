import asyncio
import logging

from rasa_sdk import utils
from rasa_sdk.constants import APPLICATION_ROOT_LOGGER_NAME
from rasa_sdk.endpoint import create_argument_parser, run
from rasa_sdk.executor import ActionExecutor
from rasa_sdk.grpc_server import run_grpc

logger = logging.getLogger(__name__)


def main_from_args(args):
    """Run with arguments."""
    logging.getLogger("matplotlib").setLevel(logging.WARN)

    utils.configure_colored_logging(args.loglevel)
    utils.configure_file_logging(
        logging.getLogger(APPLICATION_ROOT_LOGGER_NAME),
        args.log_file,
        args.loglevel,
        args.logging_config_file,
    )
    utils.update_sanic_log_level()

    action_executor = ActionExecutor()
    action_executor.register_package(
        args.actions_module or args.actions,
    )

    if args.grpc:
        asyncio.run(
            run_grpc(
                action_executor,
                args.port,
                args.ssl_certificate,
                args.ssl_keyfile,
                args.ssl_ca_file,
                args.auto_reload,
                args.endpoints,
            )
        )
    else:
        run(
            action_executor,
            args.port,
            args.cors,
            args.ssl_certificate,
            args.ssl_keyfile,
            args.ssl_password,
            args.auto_reload,
            args.endpoints,
        )


def main():
    """Runs the action server as standalone application."""
    arg_parser = create_argument_parser()
    cmdline_args = arg_parser.parse_args()

    main_from_args(cmdline_args)


if __name__ == "__main__":
    main()
