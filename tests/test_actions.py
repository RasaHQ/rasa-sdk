from typing import List, Dict, Text, Any

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict


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
