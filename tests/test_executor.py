import os
import shutil
import random
import string
import time

from typing import Text, Optional, Generator

import pytest
from rasa_sdk.executor import ActionExecutor, CollectingDispatcher
from tests.conftest import SubclassTestActionA, SubclassTestActionB

TEST_PACKAGE_BASE = "tests/executor_test_packages"

ACTION_TEMPLATE = """
from rasa_sdk import Action

class {class_name}(Action):
    def name(self):
        return "{action_name}"

    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message("{message}")
        return []
"""


def _write_action_file(
    package_path: Text,
    file_name: Text,
    class_name: Text,
    action_name: Text,
    message: Optional[Text] = None,
) -> None:
    with open(os.path.join(package_path, file_name), "w") as f:
        f.write(
            ACTION_TEMPLATE.format(
                class_name=class_name, action_name=action_name, message=message
            )
        )


@pytest.mark.parametrize(
    "noevent", [1, ["asd"], "asd", 3.2, None, {"event_without_event_property": 4}]
)
def test_event_validation_fails_on_odd_things(noevent):
    assert ActionExecutor.validate_events([noevent], "myaction") == []


def test_event_validation_accepts_dicts_with_event():
    assert ActionExecutor.validate_events([{"event": "user"}], "myaction") == [
        {"event": "user"}
    ]


def test_deprecated_utter_elements():
    dispatcher = CollectingDispatcher()
    with pytest.warns(FutureWarning):
        dispatcher.utter_elements(1, 2, 3)

    assert dispatcher.messages[0] == {
        "text": None,
        "buttons": [],
        "elements": [1, 2, 3],
        "custom": {},
        "template": None,
        "response": None,
        "image": None,
        "attachment": None,
    }


def test_utter_message_with_template_param():
    dispatcher = CollectingDispatcher()
    with pytest.warns(FutureWarning):
        dispatcher.utter_message(template="utter_greet")

    assert dispatcher.messages[0] == {
        "text": None,
        "buttons": [],
        "elements": [],
        "custom": {},
        "template": "utter_greet",
        "response": "utter_greet",
        "image": None,
        "attachment": None,
    }


def test_utter_message_with_response_param():
    dispatcher = CollectingDispatcher()
    dispatcher.utter_message(response="utter_greet")

    assert dispatcher.messages[0] == {
        "text": None,
        "buttons": [],
        "elements": [],
        "custom": {},
        "template": "utter_greet",
        "response": "utter_greet",
        "image": None,
        "attachment": None,
    }


@pytest.fixture()
def package_path() -> Generator[Text, None, Text]:
    # Create an empty directory somewhere reached by the Python import search
    # paths
    name = "".join(random.choice(string.ascii_lowercase) for _ in range(10))
    package_path = os.path.join(TEST_PACKAGE_BASE, name)

    # Ensure package dir is clean
    shutil.rmtree(package_path, ignore_errors=True)
    os.makedirs(package_path)
    yield package_path

    # Cleanup
    shutil.rmtree(package_path, ignore_errors=True)


@pytest.fixture()
def executor() -> ActionExecutor:
    return ActionExecutor()


@pytest.fixture()
def dispatcher() -> CollectingDispatcher:
    return CollectingDispatcher()


def test_load_action_from_init(executor: ActionExecutor, package_path: Text):
    # Actions should be loaded from packages
    _write_action_file(package_path, "__init__.py", "InitAction", "init_action")
    executor.register_package(package_path.replace("/", "."))

    assert "init_action" in executor.actions


def test_load_submodules_in_package(executor: ActionExecutor, package_path: Text):
    # If there's submodules inside a package, they should be picked up correctly
    _write_action_file(package_path, "__init__.py", "Action1", "action1")
    _write_action_file(package_path, "a1.py", "Action2", "action2")
    _write_action_file(package_path, "a2.py", "Action3", "action3")

    executor.register_package(package_path.replace("/", "."))

    for name in ["action1", "action2", "action3"]:
        assert name in executor.actions


def test_load_submodules_in_namespace_package(
    executor: ActionExecutor, package_path: Text
):
    # If there's submodules inside a namespace package (a package without
    # __init__.py), they should be picked up correctly
    _write_action_file(package_path, "foo.py", "FooAction", "foo_action")
    _write_action_file(package_path, "bar.py", "BarAction", "bar_action")

    executor.register_package(package_path.replace("/", "."))

    for name in ["foo_action", "bar_action"]:
        assert name in executor.actions


def test_load_module_directly(executor: ActionExecutor, package_path: Text):
    _write_action_file(
        package_path, "test_module.py", "TestModuleAction", "test_module_action"
    )

    # Load a module directly, not a package. This is equivalent to loading
    # "action" when there's an "action.py" file in the module search path.
    executor.register_package(package_path.replace("/", ".") + ".test_module")

    assert "test_module_action" in executor.actions


async def test_reload_module(
    executor: ActionExecutor, dispatcher: CollectingDispatcher, package_path: Text
):
    action_class = "MyAction"
    action_file = "my_action.py"
    action_name = "my_action"

    _write_action_file(
        package_path, action_file, action_class, action_name, message="foobar"
    )

    executor.register_package(package_path.replace("/", "."))

    action_v1 = executor.actions.get(action_name)
    assert action_v1

    await action_v1(dispatcher, None, None)

    assert dispatcher.messages[0] == {
        "text": "foobar",
        "buttons": [],
        "elements": [],
        "custom": {},
        "template": None,
        "response": None,
        "image": None,
        "attachment": None,
    }

    # Write the action file again, but change its contents
    _write_action_file(
        package_path, action_file, action_class, action_name, message="hello!"
    )

    # Manually set the file's timestamp 10 seconds into the future, otherwise
    # Python will load the class already compiled in __pycache__, which is the
    # previous version.
    mod_time = time.time() + 10
    os.utime(os.path.join(package_path, action_file), times=(mod_time, mod_time))

    # Reload modules
    executor.reload()
    dispatcher.messages.clear()

    action_v2 = executor.actions.get(action_name)
    assert action_v2

    await action_v2(dispatcher, None, None)

    # The message should have changed
    assert dispatcher.messages[0] == {
        "text": "hello!",
        "buttons": [],
        "elements": [],
        "custom": {},
        "template": None,
        "response": None,
        "image": None,
        "attachment": None,
    }


def test_load_subclasses(executor: ActionExecutor):
    executor.register_action(SubclassTestActionB)
    assert list(executor.actions) == ["subclass_test_action_b"]

    executor.register_action(SubclassTestActionA)
    assert sorted(list(executor.actions)) == [
        "subclass_test_action_a",
        "subclass_test_action_b",
    ]


async def test_reload_discovers_new_modules(
    executor: ActionExecutor, dispatcher: CollectingDispatcher, package_path: Text
):
    """Test that reload discovers newly created module files."""
    # Initially register package with one action
    _write_action_file(
        package_path, "action1.py", "Action1", "action_1", message="action 1"
    )

    executor.register_package(package_path.replace("/", "."))

    assert "action_1" in executor.actions
    assert "action_2" not in executor.actions

    # Create a new action file after registration
    _write_action_file(
        package_path, "action2.py", "Action2", "action_2", message="action 2"
    )

    # Set the file's timestamp into the future to ensure it's detected
    mod_time = time.time() + 10
    os.utime(os.path.join(package_path, "action2.py"), times=(mod_time, mod_time))

    # Reload should discover the new module
    executor.reload()

    # Both actions should now be registered
    assert "action_1" in executor.actions
    assert "action_2" in executor.actions

    # Test that the new action works
    action_2 = executor.actions.get("action_2")
    assert action_2

    await action_2(dispatcher, None, None)

    assert dispatcher.messages[0]["text"] == "action 2"


async def test_reload_discovers_new_modules_in_namespace_package(
    executor: ActionExecutor, dispatcher: CollectingDispatcher, package_path: Text
):
    """Test that reload discovers newly created modules in namespace packages."""
    # Start with a namespace package (no __init__.py) with one module
    _write_action_file(
        package_path, "foo.py", "FooAction", "foo_action", message="foo"
    )

    executor.register_package(package_path.replace("/", "."))

    # Get initial action count
    initial_action_count = len(executor.actions)
    assert "foo_action" in executor.actions

    # Add a new module to the namespace package
    _write_action_file(
        package_path, "baz.py", "BazAction", "baz_action", message="baz"
    )

    # Set timestamp into the future
    mod_time = time.time() + 10
    os.utime(os.path.join(package_path, "baz.py"), times=(mod_time, mod_time))

    # Reload should discover the new module
    executor.reload()

    # Action count should increase by 1
    assert len(executor.actions) == initial_action_count + 1
    assert "foo_action" in executor.actions
    assert "baz_action" in executor.actions

    # Test that the new action works
    action = executor.actions.get("baz_action")
    assert action

    await action(dispatcher, None, None)
    assert dispatcher.messages[0]["text"] == "baz"


def test_reload_tracks_registered_packages(executor: ActionExecutor, package_path: Text):
    """Test that registered packages are tracked correctly."""
    _write_action_file(
        package_path, "action1.py", "Action1", "action_1", message="action 1"
    )

    package_name = package_path.replace("/", ".")
    executor.register_package(package_name)

    # Check that package is tracked
    assert package_name in executor._registered_packages


async def test_reload_with_modified_and_new_modules(
    executor: ActionExecutor, dispatcher: CollectingDispatcher, package_path: Text
):
    """Test that reload handles both modified and newly created modules."""
    # Start with one action using a unique name
    _write_action_file(
        package_path, "mod_action.py", "ModifiedAction", "modified_action", message="original"
    )

    executor.register_package(package_path.replace("/", "."))

    # Get initial action count
    initial_action_count = len(executor.actions)

    # Verify initial state
    assert "modified_action" in executor.actions
    assert "brand_new_action" not in executor.actions

    # Modify the existing action
    _write_action_file(
        package_path, "mod_action.py", "ModifiedAction", "modified_action", message="modified"
    )

    # Create a new action with a unique name
    _write_action_file(
        package_path, "new_action.py", "BrandNewAction", "brand_new_action", message="new action"
    )

    # Set timestamps into the future
    mod_time = time.time() + 10
    for file in ["mod_action.py", "new_action.py"]:
        os.utime(os.path.join(package_path, file), times=(mod_time, mod_time))

    # Reload should handle both cases
    executor.reload()

    # Action count should increase by 1 (one new action added)
    assert len(executor.actions) == initial_action_count + 1

    # Both actions should be registered
    assert "modified_action" in executor.actions
    assert "brand_new_action" in executor.actions

    # Test modified action
    action_1 = executor.actions.get("modified_action")
    await action_1(dispatcher, None, None)
    assert dispatcher.messages[0]["text"] == "modified"

    dispatcher.messages.clear()

    # Test new action
    action_2 = executor.actions.get("brand_new_action")
    await action_2(dispatcher, None, None)
    assert dispatcher.messages[0]["text"] == "new action"
