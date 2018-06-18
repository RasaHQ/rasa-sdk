from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from typing import Any, List


def all_subclasses(cls):
    # type: (Any) -> List[Any]
    """Returns all known (imported) subclasses of a class."""

    return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                   for g in all_subclasses(s)]


def configure_colored_logging(loglevel):
    import coloredlogs
    field_styles = coloredlogs.DEFAULT_FIELD_STYLES.copy()
    field_styles['asctime'] = {}
    level_styles = coloredlogs.DEFAULT_LEVEL_STYLES.copy()
    level_styles['debug'] = {}
    coloredlogs.install(
            level=loglevel,
            use_chroot=False,
            fmt='%(asctime)s %(levelname)-8s %(name)s  - %(message)s',
            level_styles=level_styles,
            field_styles=field_styles)