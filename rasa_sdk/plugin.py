import functools
import sys
from typing import Text, Tuple
import logging
import pluggy

hookspec = pluggy.HookspecMarker("rasa_sdk")
logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=2)
def plugin_manager() -> pluggy.PluginManager:
    """Initialises a plugin manager which registers hook implementations."""
    _plugin_manager = pluggy.PluginManager("rasa_sdk")
    _plugin_manager.add_hookspecs(sys.modules["rasa_sdk.plugin"])
    _discover_plugins(_plugin_manager)

    return _plugin_manager


def _discover_plugins(manager: pluggy.PluginManager) -> None:
    try:
        # rasa_sdk_plugin is a custom package
        # which extends existing functionality on rasa action server via plugins
        import rasa_sdk_plugins

        rasa_sdk_plugins.init_hooks(manager)
    except ModuleNotFoundError as e:
        logger.info("Module cannot be found", exc_info=e)
        pass


@hookspec  # type: ignore[misc]
def get_version_info() -> Tuple[Text, Text]:
    """Hook specification for getting plugin version info."""


@hookspec  # type: ignore[misc]
def attach_sanic_app_extensions(app) -> bool:
    """Hook specification for attaching sanic listeners, routes and middlewares."""
