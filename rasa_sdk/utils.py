import asyncio
import inspect
import logging
import warnings
import os

from typing import AbstractSet, Any, List, Text, Optional, Coroutine, Union

import rasa_sdk
from rasa_sdk.constants import (
    DEFAULT_SANIC_WORKERS,
    ENV_SANIC_WORKERS,
    DEFAULT_LOG_LEVEL_LIBRARIES,
    ENV_LOG_LEVEL_LIBRARIES,
)

logger = logging.getLogger(__name__)


class Element(dict):
    __acceptable_keys = ["title", "item_url", "image_url", "subtitle", "buttons"]

    def __init__(self, *args, **kwargs):
        kwargs = {
            key: value for key, value in kwargs.items() if key in self.__acceptable_keys
        }

        super().__init__(*args, **kwargs)


class Button(dict):
    pass


def all_subclasses(cls: Any) -> List[Any]:
    """Returns all known (imported) subclasses of a class."""

    return cls.__subclasses__() + [
        g for s in cls.__subclasses__() for g in all_subclasses(s)
    ]


def add_logging_option_arguments(parser):
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


def configure_colored_logging(loglevel):
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


def arguments_of(func) -> AbstractSet[Text]:
    """Return the parameters of the function `func` as a list of their names."""

    return inspect.signature(func).parameters.keys()


def number_of_sanic_workers() -> int:
    """Get the number of Sanic workers to use in `app.run()`.
    If the environment variable `constants.ENV_SANIC_WORKERS` is set and is not equal to 1.
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
        warnings.warn(
            f"Cannot set number of Sanic workers to the desired value "
            f"({env_value}). The number of workers must be at least 1."
        )
        return _log_and_get_default_number_of_workers()

    logger.debug(f"Using {env_value} Sanic workers.")
    return env_value


def check_version_compatibility(rasa_version: Optional[Text]) -> None:
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
        warnings.warn(
            f"You are using an old version of rasa which might "
            f"not be compatible with this version of rasa_sdk "
            f"({rasa_sdk.__version__}).\n"
            f"To ensure compatibility use the same version "
            f"for both, modulo the last number, i.e. using version "
            f"A.B.x the numbers A and B should be identical for "
            f"both rasa and rasa_sdk."
        )
        return

    rasa = rasa_version.split(".")[:-1]
    sdk = rasa_sdk.__version__.split(".")[:-1]

    if rasa != sdk:
        warnings.warn(
            f"Your versions of rasa and "
            f"rasa_sdk might not be compatible. You "
            f"are currently running rasa version {rasa_version} "
            f"and rasa_sdk version {rasa_sdk.__version__}.\n"
            f"To ensure compatibility use the same "
            f"version for both, modulo the last number, "
            f"i.e. using version A.B.x the numbers A and "
            f"B should be identical for "
            f"both rasa and rasa_sdk."
        )


def update_sanic_log_level() -> None:
    """Set the log level of sanic loggers.

    Use the environment variable 'LOG_LEVEL_LIBRARIES', or default to
    `DEFAULT_LOG_LEVEL_LIBRARIES` if undefined.
    """
    from sanic.log import logger, error_logger, access_logger

    log_level = os.environ.get(ENV_LOG_LEVEL_LIBRARIES, DEFAULT_LOG_LEVEL_LIBRARIES)

    logger.setLevel(log_level)
    error_logger.setLevel(log_level)
    access_logger.setLevel(log_level)

    logger.propagate = False
    error_logger.propagate = False
    access_logger.propagate = False


async def call_potential_coroutine(
    coroutine_or_return_value: Union[Any, Coroutine]
) -> Any:
    if asyncio.iscoroutine(coroutine_or_return_value):
        return await coroutine_or_return_value

    return coroutine_or_return_value
