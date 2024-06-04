import logging
import warnings

from pytest import MonkeyPatch, LogCaptureFixture
from pluggy import PluginManager
from unittest.mock import MagicMock

from rasa_sdk import endpoint
from rasa_sdk.plugin import plugin_manager


def test_plugins_not_found(caplog: LogCaptureFixture) -> None:
    """Test that a debug message is logged when no plugins are found.

    This test must be run first because the plugin manager is cached.
    """
    with caplog.at_level(logging.DEBUG):
        plugin_manager()
        assert "No plugins found: No module named 'rasa_sdk_plugins'" in caplog.text


def test_plugin_manager() -> None:
    manager = plugin_manager()
    assert isinstance(manager, PluginManager)

    manager_2 = plugin_manager()
    assert manager_2 == manager


def test_plugin_attach_sanic_app_extension(
    monkeypatch: MonkeyPatch,
) -> None:
    manager = plugin_manager()
    monkeypatch.setattr(
        manager.hook, "attach_sanic_app_extensions", MagicMock(return_value=None)
    )
    monkeypatch.setattr("rasa_sdk.endpoint.Sanic.serve", MagicMock(return_value=None))
    app_mock = MagicMock()

    # Create a MagicMock object to replace the create_app() method
    create_app_mock = MagicMock(return_value=app_mock)

    # Set the create_app() method to return create_app_mock
    monkeypatch.setattr("rasa_sdk.endpoint.create_app", create_app_mock)

    # Set the return value of app_mock.prepare() to None
    app_mock.prepare.return_value = None

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        endpoint.run("actions")
    manager.hook.attach_sanic_app_extensions.assert_called_once_with(app=app_mock)
