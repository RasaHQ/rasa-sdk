import warnings

from pytest import MonkeyPatch
from pluggy import PluginManager
from unittest.mock import MagicMock

from rasa_sdk import endpoint
from rasa_sdk.plugin import plugin_manager


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
    app_mock = MagicMock()

    # Create a MagicMock object to replace the create_app() method
    create_app_mock = MagicMock(return_value=app_mock)

    # Set the create_app() method to return create_app_mock
    monkeypatch.setattr("rasa_sdk.endpoint.create_app", create_app_mock)

    # Set the return value of app_mock.run() to None
    app_mock.run.return_value = None

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        endpoint.run("actions")
    manager.hook.attach_sanic_app_extensions.assert_called_once_with(app=app_mock)

def test_plugins_not_found(monkeypatch):
    # Mock the import statement to raise ModuleNotFoundError
    monkeypatch.setitem(__builtins__, 'import',
                        MagicMock(side_effect=ModuleNotFoundError))

    # Call the method under test
    try:
        import rasa_sdk_plugins
    except ModuleNotFoundError as e:
        # Assert the expected exception message or other details if needed
        assert str(e) == "No module named 'rasa_sdk_plugins'"
