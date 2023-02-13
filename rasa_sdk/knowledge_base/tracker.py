from rasa_sdk.interfaces import Tracker
import typing
from typing import List, Text

from rasa_sdk.events import EventType

if typing.TYPE_CHECKING:  # pragma: no cover
    from rasa_sdk.executor import CollectingDispatcher
    from rasa_sdk.types import DomainDict, TrackerState


class TrackerKnowledgeBase(Tracker):
    def __init__(
        self,
        tracker: Tracker,
    ) -> None:
        self.slots = tracker.slots
        self.events = tracker.events

    def add_object_type_slot(self, slots: List[EventType], object_type_value:Text) -> None:
        """Adds slots to the current tracker.

        Args:
            slots: `SlotSet` events.
        """
        for event in slots:
            if not event.get("event") == "slot":
                continue
            print(f"event: {event}")
            self.slots[event["name"]] = object_type_value
            self.events.append(event)