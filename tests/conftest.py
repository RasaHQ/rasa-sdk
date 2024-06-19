from typing import List, Dict, Text, Any

from sanic import Sanic

import pytest

import rasa_sdk
from rasa_sdk import Action, FormValidationAction, Tracker, ValidationAction
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict

Sanic.test_mode = True


def get_stack():
    """Return a dialogue stack."""
    dialogue_stack = [
        {
            "frame_id": "CP6JP9GQ",
            "flow_id": "check_balance",
            "step_id": "0_check_balance",
            "frame_type": "regular",
            "type": "flow",
        }
    ]
    return dialogue_stack


class CustomAsyncAction(Action):
    def name(cls) -> Text:
        return "custom_async_action"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:
        return [SlotSet("test", "foo"), SlotSet("test2", "boo")]


class CustomAction(Action):
    def name(cls) -> Text:
        return "custom_action"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:
        return [SlotSet("test", "bar")]


class CustomActionRaisingException(Action):
    def name(cls) -> Text:
        return "custom_action_exception"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:
        raise Exception("test exception")


class CustomActionWithDialogueStack(Action):
    def name(cls) -> Text:
        return "custom_action_with_dialogue_stack"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:
        return [SlotSet("stack", tracker.stack)]


class MockFormValidationAction(FormValidationAction):
    def __init__(self) -> None:
        self.fail_if_undefined("run")

    def fail_if_undefined(self, method_name: str) -> None:
        if not (
            hasattr(self.__class__.__base__, method_name)
            and callable(getattr(self.__class__.__base__, method_name))
        ):
            pytest.fail(
                f"method '{method_name}' not found in {self.__class__.__base__}. "
                f"This likely means the method was renamed, which means the "
                f"instrumentation needs to be adapted!"
            )

    async def _extract_validation_events(
        self,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> None:
        return tracker.events

    def name(self) -> str:
        return "mock_form_validation_action"


class MockValidationAction(ValidationAction):
    def __init__(self) -> None:
        self.fail_if_undefined("run")

    def fail_if_undefined(self, method_name: Text) -> None:
        if not (
            hasattr(self.__class__.__base__, method_name)
            and callable(getattr(self.__class__.__base__, method_name))
        ):
            pytest.fail(
                f"method '{method_name}' not found in {self.__class__.__base__}. "
                f"This likely means the method was renamed, which means the "
                f"instrumentation needs to be adapted!"
            )

    async def run(
        self,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> None:
        pass

    def name(self) -> Text:
        return "mock_validation_action"

    async def _extract_validation_events(
        self,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> None:
        return tracker.events


class SubclassTestActionA(Action):
    def name(self):
        return "subclass_test_action_a"


class SubclassTestActionB(SubclassTestActionA):
    def name(self):
        return "subclass_test_action_b"


@pytest.fixture
def current_rasa_version() -> str:
    """Return current Rasa version."""
    return rasa_sdk.__version__


@pytest.fixture
def previous_rasa_version() -> str:
    """Return previous Rasa version."""
    return "1.0.0"
