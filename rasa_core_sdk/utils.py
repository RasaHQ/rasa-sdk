from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import inspect

from typing import Any, List

import logging


def all_subclasses(cls):
    # type: (Any) -> List[Any]
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


def arguments_of(func):
    """Return the parameters of the function `func` as a list of their names."""

    try:
        # python 3.x is used
        return inspect.signature(func).parameters.keys()
    except AttributeError:
        # python 2.x is used
        return inspect.getargspec(func).args
