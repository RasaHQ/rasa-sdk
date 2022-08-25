import logging
from importlib import import_module, invalidate_caches
from os import environ

from rasa_sdk import utils
from rasa_sdk.constants import APPLICATION_ROOT_LOGGER_NAME
from rasa_sdk.endpoint import create_argument_parser, run

RASA_LOGGER_PYMODULE = "RASA_LOGGER_PYMODULE"


def default_logging(args):
    utils.configure_colored_logging(args.loglevel)
    utils.configure_file_logging(
        logging.getLogger(APPLICATION_ROOT_LOGGER_NAME), args.log_file, args.loglevel
    )


def main_from_args(args):
    """Run with arguments."""
    logging.getLogger("matplotlib").setLevel(logging.WARN)

    logger_path = environ.get(RASA_LOGGER_PYMODULE, "")
    if logger_path:
        try:
            invalidate_caches()
            import_module(name=logger_path)
            # update root level
            logging.getLogger(__name__).debug(f"set root level to {args.loglevel}")
            logging.basicConfig(level=args.loglevel, force=True)
        except Exception as e:
            default_logging(args)
            logging.getLogger(__name__).exception("custom logger import failed", exc_info=e)
    else:
        default_logging(args)

    utils.update_sanic_log_level()

    run(
        args.actions,
        args.port,
        args.cors,
        args.ssl_certificate,
        args.ssl_keyfile,
        args.ssl_password,
        args.auto_reload,
    )


def main():
    # Running as standalone python application
    arg_parser = create_argument_parser()
    cmdline_args = arg_parser.parse_args()

    main_from_args(cmdline_args)


if __name__ == "__main__":
    main()
