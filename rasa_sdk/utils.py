import inspect
import logging
import os
from typing import Any, List, Text

from rasa_sdk.constants import DEFAULT_SANIC_WORKERS, ENV_SANIC_WORKERS

logger = logging.getLogger(__name__)

class Element(dict):
    __acceptable_keys = ["title", "item_url", "image_url", "subtitle", "buttons"]

    def __init__(self, *args, **kwargs):
        kwargs = {
            key: value for key, value in kwargs.items() if key in self.__acceptable_keys
        }

        super(Element, self).__init__(*args, **kwargs)


class Button(dict):
    pass


def all_subclasses(cls: Any) -> List[Any]:
    """Returns all known (imported) subclasses of a class."""

    return cls.__subclasses__() + [
        g for s in cls.__subclasses__() for g in all_subclasses(s)
    ]


def add_logging_option_arguments(parser) -> None:
    """Add options to an argument parser to configure logging levels."""

    # arguments for logging configuration
    parser.add_argument(
        "-v",
        "--verbose",
        help="Be verbose. Sets logging level to INFO",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
        default=logging.INFO,
    )
    parser.add_argument(
        "-vv",
        "--debug",
        help="Print lots of debugging statements. Sets logging level to DEBUG",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
    )
    parser.add_argument(
        "--quiet",
        help="Be quiet! Sets logging level to WARNING",
        action="store_const",
        dest="loglevel",
        const=logging.WARNING,
    )


def configure_colored_logging(loglevel) -> None:
    import coloredlogs

    field_styles = coloredlogs.DEFAULT_FIELD_STYLES.copy()
    field_styles["asctime"] = {}
    level_styles = coloredlogs.DEFAULT_LEVEL_STYLES.copy()
    level_styles["debug"] = {}
    coloredlogs.install(
        level=loglevel,
        use_chroot=False,
        fmt="%(asctime)s %(levelname)-8s %(name)s  - %(message)s",
        level_styles=level_styles,
        field_styles=field_styles,
    )


def arguments_of(func) -> List[Text]:
    """Return the parameters of the function `func` as a list of their names."""

    return inspect.signature(func).parameters.keys()


def number_of_sanic_workers() -> int:
    """Get the number of Sanic workers to use in `app.run()`.
    If the environment variable constants.ENV_SANIC_WORKERS is set and is not equal to
    1, that value will only be permitted if the used lock store supports shared
    resources across multiple workers (e.g. ``RedisLockStore``).
    """

    def _log_and_get_default_number_of_workers():
        logger.debug(
            f"Using the default number of Sanic workers ({DEFAULT_SANIC_WORKERS})."
        )
        return DEFAULT_SANIC_WORKERS

    try:
        env_value = int(os.environ.get(ENV_SANIC_WORKERS, DEFAULT_SANIC_WORKERS))
    except ValueError:
        logger.error(
            f"Cannot convert environment variable `{ENV_SANIC_WORKERS}` "
            f"to int ('{os.environ[ENV_SANIC_WORKERS]}')."
        )
        return _log_and_get_default_number_of_workers()

    if env_value == DEFAULT_SANIC_WORKERS:
        return _log_and_get_default_number_of_workers()

    if env_value < 1:
        logger.debug(
            f"Cannot set number of Sanic workers to the desired value "
            f"({env_value}). The number of workers must be at least 1."
        )
        return _log_and_get_default_number_of_workers()

    logger.debug(f"Using {env_value} Sanic workers.")
    return env_value
