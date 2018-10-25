# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import typing
from typing import Dict, Text, Any, List, Union, Optional

from rasa_core_sdk import Action, ActionExecutionRejection
from rasa_core_sdk.events import SlotSet, Form

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from rasa_core_sdk import Tracker
    from rasa_core_sdk.executor import CollectingDispatcher

# this slot is used to store information needed
# to do the form handling
REQUESTED_SLOT = "requested_slot"


class FormAction(Action):

    def name(self):
        # type: () -> Text
        """Unique identifier of the form"""

        raise NotImplementedError("A form must implement a name")

    @staticmethod
    def required_slots(tracker):
        # type: (Tracker) -> List[Text]
        """A list of required slots that the form has to fill"""

        raise NotImplementedError("A form must implement required slots "
                                  "that it has to fill")

    @staticmethod
    def from_entity(entity, intent=None):
        return {"type": "from_entity", "intent": intent, "entity": entity}

    @staticmethod
    def from_intent(intent, value):
        return {"type": "from_intent", "intent": intent, "value": value}

    @staticmethod
    def from_text(intent=None):
        return {"type": "from_text", "intent": intent}

    # noinspection PyMethodMayBeStatic
    def slots_mappings(self):
        # type: () -> Dict[Text: Union[Dict, List[Dict]]]
        """A dictionary to map required slots to
            - an extracted entity
            - intent: value pairs
            - a whole message
            or a list of them, where a first match will be picked

            Empty dict is converted to a mapping of
            the slot to the extracted entity with the same name
        """

        return {}

    # noinspection PyUnusedLocal
    def extract(self,
                dispatcher,  # type: CollectingDispatcher
                tracker,  # type: Tracker
                domain  # type: Dict[Text, Any]
                ):
        # type: (...) -> Optional[List[Dict]]
        """"Extract requested slot from a user input else return None"""
        slot_to_fill = tracker.get_slot(REQUESTED_SLOT)

        # map requested_slot to entity
        requested_slot_mappings = self.slots_mappings().get(slot_to_fill)
        if not requested_slot_mappings:
            requested_slot_mappings = self.from_entity(slot_to_fill)

        if not isinstance(requested_slot_mappings, list):
            requested_slot_mappings = [requested_slot_mappings]

        for requested_slot_mapping in requested_slot_mappings:
            if (not isinstance(requested_slot_mapping, dict) or
                    requested_slot_mapping.get("type") is None):
                raise TypeError("Provided incompatible slot_mapping")

            mapping_intent = requested_slot_mapping.get("intent")
            intent = tracker.latest_message.get("intent",
                                                {}).get("name")
            if mapping_intent is None or mapping_intent == intent:
                mapping_type = requested_slot_mapping["type"]

                if mapping_type == "from_entity":
                    entity_value = next(tracker.get_latest_entity_values(
                            requested_slot_mapping.get("entity")), None)
                    if entity_value is not None:
                        return [SlotSet(slot_to_fill, entity_value)]

                elif mapping_type == "from_intent":
                    return [SlotSet(slot_to_fill,
                                    requested_slot_mapping.get("value"))]

                elif mapping_type == "from_text":
                    return [SlotSet(slot_to_fill,
                                    tracker.latest_message.get("text"))]

                else:
                    raise ValueError(
                            'Provided slot_mapping["type"] '
                            'is not supported')

        return None

    # noinspection PyUnusedLocal
    def validate(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """"Validate extracted requested slot else raise an error"""
        slot_to_fill = tracker.get_slot(REQUESTED_SLOT)

        events = self.extract(dispatcher, tracker, domain)

        if events is not None:
            return events
        else:
            raise ActionExecutionRejection(self.name(),
                                           "Failed to validate slot {0} "
                                           "with action {1}"
                                           "".format(slot_to_fill,
                                                     self.name()))

    # noinspection PyUnusedLocal
    def request_next_slot(self,
                          dispatcher,  # type: CollectingDispatcher
                          tracker,  # type: Tracker
                          domain  # type: Dict[Text, Any]
                          ):
        # type: (...) -> Optional[List[Dict]]
        """"Request the next slot and utter template if needed,
            else return None"""

        for slot in self.required_slots(tracker):
            if self._should_request_slot(tracker, slot):
                dispatcher.utter_template("utter_ask_{}".format(slot), tracker)
                return [SlotSet(REQUESTED_SLOT, slot)]

        return None

    def submit(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """Define what the form has to do
            after all required slots are filled"""

        raise NotImplementedError("A form must implement a submit method")

    # run helpers
    def _activate_if_required(self, tracker):
        # type: (Tracker) -> List[Dict]
        """Return `Form` event with the name of the form
            if the form was called for the first time"""

        if tracker.active_form == self.name():
            return []
        else:
            return [Form(self.name())]

    @staticmethod
    def _predicted_no_validation(tracker):
        # type: (Tracker) -> bool
        """Check whether validation should be skipped"""
        for e in reversed(tracker.events):
            if e['event'] == 'no_form_validation':
                return True
            elif e['event'] == 'action':
                return False

        return False

    def _validate_if_required(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """Return a list of events from `self.validate`
            if validation is required:
            - the form is active
            - the form is called after `action_listen`
        """
        if (tracker.active_form == self.name() and
                tracker.latest_action_name == 'action_listen' and
                not self._predicted_no_validation(tracker)):
            return self.validate(dispatcher, tracker, domain)
        else:
            return []

    @staticmethod
    def _should_request_slot(tracker, slot_name):
        # type: (Tracker, Text) -> bool
        """Check whether form action should request given slot"""

        return tracker.get_slot(slot_name) is None

    @staticmethod
    def _deactivate():
        # type: () -> List[Dict]
        """Return `Form` event with `None` as name to deactivate the form
            and reset the requested slot"""

        return [Form(None), SlotSet(REQUESTED_SLOT, None)]

    def run(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """Execute the side effects of this form:
            - activate if needed
            - validate user input if needed
            - set validated slots
            - utter_ask_{slot} template with the next required slot
            - submit the form if all required slots are set
            - deactivate the form
        """
        # activate the form
        events = self._activate_if_required(tracker)
        # validate user input
        events.extend(self._validate_if_required(dispatcher, tracker, domain))

        temp_tracker = tracker.copy()
        for e in events:
            if e['event'] == 'slot':
                temp_tracker.slots[e["name"]] = e["value"]

        next_slot_events = self.request_next_slot(dispatcher, temp_tracker,
                                                  domain)
        if next_slot_events is not None:
            # request next slot
            events.extend(next_slot_events)
        else:
            # there is nothing more to request, so we can submit
            events.extend(self.submit(dispatcher, temp_tracker, domain))
            # deactivate the form after submission
            events.extend(self._deactivate())

        return events

    def __str__(self):
        return "FormAction('{}')".format(self.name())
