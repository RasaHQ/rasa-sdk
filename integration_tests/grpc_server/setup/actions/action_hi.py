from typing import Any, Dict

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher


class ActionHi(Action):

    def name(self) -> str:
        return "action_hi"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[str, Any]):
        dispatcher.utter_message(text="Hi")
        return []
