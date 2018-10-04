from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import copy
import logging

import typing
from typing import Dict, Text, Any, Optional, Iterator, List

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from rasa_core_sdk.executor import CollectingDispatcher


class Tracker(object):
    """Maintains the state of a conversation."""

    @classmethod
    def from_dict(cls, state):
        # type: (Dict[Text, Any]) -> Tracker
        """Create a tracker from dump."""

        return Tracker(state.get("sender_id"),
                       state.get("slots", {}),
                       state.get("latest_message", {}),
                       state.get("events"),
                       state.get("paused"),
                       state.get("followup_action"),
                       state.get("active_form"),
                       state.get("latest_action_name"))

    def __init__(self, sender_id, slots,
                 latest_message, events, paused, followup_action, active_form, latest_action_name):
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
        self.active_form = active_form
        self.latest_action_name = latest_action_name

    def current_state(self):
        # type: () -> Dict[Text, Any]
        """Return the current tracker state as an object."""

        if len(self.events) > 0:
            latest_event_time = self.events[-1].timestamp
        else:
            latest_event_time = None

        return {
            "sender_id": self.sender_id,
            "slots": self.slots,
            "latest_message": self.latest_message,
            "latest_event_time": latest_event_time,
            "paused": self.is_paused(),
            "events": self.events,
            "active_form": self.active_form,
            "latest_action_name": self.latest_action_name
        }

    def current_slot_values(self):
        # type: () -> Dict[Text, Any]
        """Return the currently set values of the slots"""
        return self.slots

    def get_slot(self, key):
        # type: (Text) -> Optional[Any]
        """Retrieves the value of a slot."""

        if key in self.slots:
            return self.slots[key]
        else:
            logger.info("Tried to access non existent slot '{}'".format(key))
            return None

    def get_latest_entity_values(self, entity_type):
        # type: (Text) -> Iterator[Text]
        """Get entity values found for the passed entity name in latest msg.

        If you are only interested in the first entity of a given type use
        `next(tracker.get_latest_entity_values("my_entity_name"), None)`.
        If no entity is found `None` is the default result."""

        entities = self.latest_message.get("entities", [])
        return (x.get("value")
                for x in entities
                if x.get("entity") == entity_type)

    def is_paused(self):
        # type: () -> bool
        """State whether the tracker is currently paused."""
        return self._paused

    def idx_after_latest_restart(self):
        # type: () -> int
        """Return the idx of the most recent restart in the list of events.

        If the conversation has not been restarted, ``0`` is returned."""

        idx = 0
        for i, event in enumerate(self.events):
            if event.get("event") == "restarted":
                idx = i + 1
        return idx

    def events_after_latest_restart(self):
        # type: () -> List[dict]
        """Return a list of events after the most recent restart."""
        return list(self.events)[self.idx_after_latest_restart():]

    def __eq__(self, other):
        if isinstance(self, type(other)):
            return (other.events == self.events and
                    self.sender_id == other.sender_id)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def copy(self):
        return Tracker(self.sender_id,
                       copy.deepcopy(self.slots),
                       copy.deepcopy(self.latest_message),
                       copy.deepcopy(self.events),
                       self._paused,
                       self.followup_action,
                       self.active_form,
                       self.latest_action_name)


class Action(object):
    """Next action to be taken in response to a dialogue state."""

    def name(self):
        # type: () -> Text
        """Unique identifier of this simple action."""

        raise NotImplementedError("An action must implement a name")

    def run(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """Execute the side effects of this action."""

        raise NotImplementedError("An action must implement its run method")

    def __str__(self):
        return "Action('{}')".format(self.name())


class ActionExecutionRejected(Exception):

    def __init__(self, action_name, message=None):
        self.action_name = action_name
        self.message = (message or
                        "Custom action '{}' rejected to run"
                        "".format(action_name))

    def __str__(self):
        return self.message
