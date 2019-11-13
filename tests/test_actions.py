from typing import List, Dict, Text, Any

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import ActionExecutor, CollectingDispatcher
from rasa_sdk.utils import is_coroutine_action


class CustomAsyncAction(Action):
    @classmethod
    def name(cls) -> Text:
        return "custom_async_action"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        return [SlotSet("test", "foo")]


class CustomActionBase(Action):
    @classmethod
    def name(cls) -> Text:
        # Name method needed to test if base action was registered
        return "base_action"

    class Meta:
        abstract = True

    @staticmethod
    def some_common_feature() -> Text:
        return "test"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        raise NotImplementedError


class CustomAction(CustomActionBase):
    @classmethod
    def name(cls) -> Text:
        return "custom_action"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        return [SlotSet("test", self.some_common_feature())]


def test_action_registration():
    executor = ActionExecutor()
    executor.register_package("tests")
    assert CustomAction.name() in executor.actions
    assert CustomActionBase.name() not in executor.actions


def test_abstract_action():
    dispatcher = CollectingDispatcher()
    tracker = Tracker("test", {}, {}, [], False, None, {}, "listen")
    domain = {}

    events = CustomAction().run(dispatcher, tracker, domain)
    assert events == [SlotSet("test", "test")]


def test_action_async_check():
    assert is_coroutine_action(CustomAction.run) == False
    assert is_coroutine_action(CustomAsyncAction.run)
