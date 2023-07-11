import functools
import sys
import logging
import pluggy

from sanic import Sanic

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
        logger.debug("No plugins found: %s", e)
        pass


@hookspec
def attach_sanic_app_extensions(app: Sanic) -> None:
    """Hook specification for attaching sanic listeners, routes and middlewares."""
