import copy
import logging
import typing
import warnings
from typing import Any, Dict, Iterator, List, Optional, Text

from rasa_sdk.events import EventType

if typing.TYPE_CHECKING:  # pragma: no cover
    from rasa_sdk.executor import CollectingDispatcher
    from rasa_sdk.types import DomainDict, TrackerState


logger = logging.getLogger(__name__)

ACTION_LISTEN_NAME = "action_listen"
NLU_FALLBACK_INTENT_NAME = "nlu_fallback"


class Tracker:
    """Maintains the state of a conversation."""

    @classmethod
    def from_dict(cls, state: "TrackerState") -> "Tracker":
        """Create a tracker from dump."""

        return Tracker(
            state["sender_id"],
            state.get("slots", {}),
            state.get("latest_message", {}),
            state.get("events", []),
            state.get("paused", False),
            state.get("followup_action"),
            state.get("active_loop", state.get("active_form", {})),
            state.get("latest_action_name"),
        )

    def __init__(
        self,
        sender_id: Text,
        slots: Dict[Text, Any],
        latest_message: Optional[Dict[Text, Any]],
        events: List[Dict[Text, Any]],
        paused: bool,
        followup_action: Optional[Text],
        active_loop: Dict[Text, Any],
        latest_action_name: Optional[Text],
    ) -> None:
        """Initialize the tracker."""

        # list of previously seen events
        self.events = events
        # id of the source of the messages
        self.sender_id = sender_id
        # slots that can be filled in this domain
        self.slots = slots

        self.followup_action = followup_action

        self._paused = paused

        # latest_message is `parse_data`,
        # which is a dict: {"intent": UserUttered.intent,
        #                   "entities": UserUttered.entities,
        #                   "text": text}
        self.latest_message = latest_message if latest_message else {}
        self.active_loop = active_loop
        self.latest_action_name = latest_action_name

    @property
    def active_form(self) -> Dict[Text, Any]:
        warnings.warn(
            "Use of `active_form` is deprecated. Please use `active_loop insteaad.",
            DeprecationWarning,
        )
        return self.active_loop

    def current_state(self) -> Dict[Text, Any]:
        """Return the current tracker state as an object."""

        if len(self.events) > 0:
            latest_event_time = self.events[-1].get("timestamp")
        else:
            latest_event_time = None

        return {
            "sender_id": self.sender_id,
            "slots": self.slots,
            "latest_message": self.latest_message,
            "latest_event_time": latest_event_time,
            "paused": self.is_paused(),
            "events": self.events,
            "latest_input_channel": self.get_latest_input_channel(),
            "active_loop": self.active_loop,
            "latest_action_name": self.latest_action_name,
        }

    def current_slot_values(self) -> Dict[Text, Any]:
        """Return the currently set values of the slots"""
        return self.slots

    def get_slot(self, key) -> Optional[Any]:
        """Retrieves the value of a slot."""

        if key in self.slots:
            return self.slots[key]
        else:
            logger.info(f"Tried to access non existent slot '{key}'.")
            return None

    def get_latest_entity_values(
        self,
        entity_type: Text,
        entity_role: Optional[Text] = None,
        entity_group: Optional[Text] = None,
    ) -> Iterator[Text]:
        """Get entity values found for the passed entity type and optional role and
        group in latest message.

        If you are only interested in the first entity of a given type use
        `next(tracker.get_latest_entity_values("my_entity_name"), None)`.
        If no entity is found `None` is the default result.

        Args:
            entity_type: the entity type of interest
            entity_role: optional entity role of interest
            entity_group: optional entity group of interest

        Returns:
            List of entity values.
        """

        entities = self.latest_message.get("entities", [])
        return (
            x.get("value")
            for x in entities
            if x.get("entity") == entity_type
            and (entity_group is None or x.get("group") == entity_group)
            and (entity_role is None or x.get("role") == entity_role)
        )

    def get_latest_input_channel(self) -> Optional[Text]:
        """Get the name of the input_channel of the latest UserUttered event"""

        for e in reversed(self.events):
            if e.get("event") == "user":
                return e.get("input_channel")
        return None

    def is_paused(self) -> bool:
        """State whether the tracker is currently paused."""
        return self._paused

    def idx_after_latest_restart(self) -> int:
        """Return the idx of the most recent restart in the list of events.

        If the conversation has not been restarted, `0` is returned.
        """
        idx = 0
        for i, event in enumerate(self.events):
            if event.get("event") == "restart":
                idx = i + 1
        return idx

    def events_after_latest_restart(self) -> List[dict]:
        """Return a list of events after the most recent restart."""
        return list(self.events)[self.idx_after_latest_restart() :]

    def __eq__(self, other: Any) -> bool:
        if isinstance(self, type(other)):
            return other.events == self.events and self.sender_id == other.sender_id
        else:
            return False

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def copy(self) -> "Tracker":
        return Tracker(
            self.sender_id,
            copy.deepcopy(self.slots),
            copy.deepcopy(self.latest_message),
            copy.deepcopy(self.events),
            self._paused,
            self.followup_action,
            self.active_loop,
            self.latest_action_name,
        )

    def last_executed_action_has(self, name: Text, skip: int = 0) -> bool:
        last = self.get_last_event_for(
            "action", exclude=[ACTION_LISTEN_NAME], skip=skip
        )
        return last is not None and last["name"] == name

    def get_last_event_for(
        self, event_type: Text, exclude: List[Text] = [], skip: int = 0
    ) -> Optional[Dict[Text, Any]]:
        def filter_function(e: Dict[Text, Any]) -> bool:
            has_instance = e["event"] == event_type
            excluded = e["event"] == "action" and e["name"] in exclude

            return has_instance and not excluded

        filtered = filter(filter_function, reversed(self.applied_events()))
        for _ in range(skip):
            next(filtered, None)

        return next(filtered, None)

    def applied_events(self) -> List[Dict[Text, Any]]:
        """Returns all actions that should be applied - w/o reverted events."""

        def undo_till_previous(event_type: Text, done_events: List[Dict[Text, Any]]):
            """Removes events from `done_events` until the first
            occurrence `event_type` is found which is also removed."""
            # list gets modified - hence we need to copy events!
            for e in reversed(done_events[:]):
                del done_events[-1]
                if e["event"] == event_type:
                    break

        applied_events: List[Dict[Text, Any]] = []
        for event in self.events:
            event_type = event.get("event")
            if event_type == "restart":
                applied_events = []
            elif event_type == "undo":
                undo_till_previous("action", applied_events)
            elif event_type == "rewind":
                # Seeing a user uttered event automatically implies there was
                # a listen event right before it, so we'll first rewind the
                # user utterance, then get the action right before it (also removes
                # the `action_listen` action right before it).
                undo_till_previous("user", applied_events)
                undo_till_previous("action", applied_events)
            else:
                applied_events.append(event)
        return applied_events

    def slots_to_validate(self) -> Dict[Text, Any]:
        """Get slots which were recently set.

        This can e.g. be used to validate form slots after they were extracted.

        Returns:
            A mapping of extracted slot candidates and their values.
        """

        slots: Dict[Text, Any] = {}
        count: int = 0

        for event in reversed(self.events):
            # The `FormAction` in Rasa Open Source will append all slot candidates
            # at the end of the tracker events.
            if event["event"] == "slot":
                count += 1
            else:
                # Stop as soon as there is another event type as this means that we
                # checked all potential slot candidates.
                break

        for event in self.events[len(self.events) - count :]:
            slots[event["name"]] = event["value"]

        return slots

    def add_slots(self, slots: List[EventType]) -> None:
        """Adds slots to the current tracker.

        Args:
            slots: `SlotSet` events.
        """
        for event in slots:
            if not event.get("event") == "slot":
                continue
            self.slots[event["name"]] = event["value"]
            self.events.append(event)

    def get_intent_of_latest_message(
        self, skip_fallback_intent: bool = True
    ) -> Optional[Text]:
        """Retrieves the intent the last user message.

        Args:
            skip_fallback_intent: Optionally skip the nlu_fallback intent
                and return the next.

        Returns:
            Intent of latest message if available.
        """
        latest_message = self.latest_message
        if not latest_message:
            return None

        intent_ranking = latest_message.get("intent_ranking")
        if not intent_ranking:
            return None

        highest_ranking_intent = intent_ranking[0]
        if (
            highest_ranking_intent["name"] == NLU_FALLBACK_INTENT_NAME
            and skip_fallback_intent
        ):
            if len(intent_ranking) >= 2:
                return intent_ranking[1]["name"]
            else:
                return None
        else:
            return highest_ranking_intent["name"]


class Action:
    """Next action to be taken in response to a dialogue state."""

    def name(self) -> Text:
        """Unique identifier of this simple action."""

        raise NotImplementedError("An action must implement a name")

    async def run(
        self,
        dispatcher: "CollectingDispatcher",
        tracker: Tracker,
        domain: "DomainDict",
    ) -> List[Dict[Text, Any]]:
        """Execute the side effects of this action.

        Args:
            dispatcher: the dispatcher which is used to
                send messages back to the user. Use
                `dispatcher.utter_message()` for sending messages.
            tracker: the state tracker for the current
                user. You can access slot values using
                `tracker.get_slot(slot_name)`, the most recent user message
                is `tracker.latest_message.text` and any other
                `rasa_sdk.Tracker` property.
            domain: the bot's domain
        Returns:
            A dictionary of `rasa_sdk.events.Event` instances that is
                returned through the endpoint
        """

        raise NotImplementedError("An action must implement its run method")

    def __str__(self) -> Text:
        return f"Action('{self.name()}')"


class ActionExecutionRejection(Exception):
    """Raising this exception will allow other policies
    to predict another action"""

    def __init__(self, action_name: Text, message: Optional[Text] = None) -> None:
        self.action_name = action_name
        self.message = message or f"Custom action '{action_name}' rejected execution."

    def __str__(self) -> Text:
        return self.message


class ActionNotFoundException(Exception):
    def __init__(self, action_name: Text, message: Optional[Text] = None) -> None:
        self.action_name = action_name
        self.message = (
            message or f"No registered action found for name '{action_name}'."
        )

    def __str__(self) -> Text:
        return self.message
