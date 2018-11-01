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
        # type: (Text, Optional[Text]) -> Dict[Text: Any]
        """A dictionary for slot mapping to extract slot value from
            - an extracted entity
        """
        return {"type": "from_entity", "intent": intent, "entity": entity}

    @staticmethod
    def from_intent(intent, value):
        # type: (Optional[Text], Any) -> Dict[Text: Any]
        """A dictionary for slot mapping to extract slot value from
            - intent: value pair
        """
        return {"type": "from_intent", "intent": intent, "value": value}

    @staticmethod
    def from_text(intent=None):
        # type: (Optional[Text]) -> Dict[Text: Any]
        """A dictionary for slot mapping to extract slot value from
            - a whole message
        """
        return {"type": "from_text", "intent": intent}

    # noinspection PyMethodMayBeStatic
    def slot_mappings(self):
        # type: () -> Dict[Text: Union[Dict, List[Dict]]]
        """A dictionary to map required slots to
            - an extracted entity
            - intent: value pairs
            - a whole message
            or a list of them, where the first match will be picked

            Empty dict is converted to a mapping of
            the slot to the extracted entity with the same name
        """

        return {}

    # noinspection PyUnusedLocal
    def extract_requested_slot(self,
                               dispatcher,  # type: CollectingDispatcher
                               tracker,  # type: Tracker
                               domain  # type: Dict[Text, Any]
                               ):
        # type: (...) -> Dict[Text: Any]
        """Extract the value of requested slot from a user input
            else return None
        """
        slot_to_fill = tracker.get_slot(REQUESTED_SLOT)
        logger.debug("Trying to extract requested slot '{}' ..."
                     "".format(slot_to_fill))
        logger.debug("... from user input '{}'".format(tracker.latest_message))

        # get mapping for requested slot
        requested_slot_mappings = self.slot_mappings().get(slot_to_fill)
        if not requested_slot_mappings:
            # map requested slot to entity
            requested_slot_mappings = self.from_entity(slot_to_fill)

        if not isinstance(requested_slot_mappings, list):
            requested_slot_mappings = [requested_slot_mappings]

        for requested_slot_mapping in requested_slot_mappings:
            logger.debug("Got mapping '{}'".format(requested_slot_mapping))

            if (not isinstance(requested_slot_mapping, dict) or
                    requested_slot_mapping.get("type") is None):
                raise TypeError("Provided incompatible slot mapping")

            mapping_intent = requested_slot_mapping.get("intent")
            intent = tracker.latest_message.get("intent",
                                                {}).get("name")
            if mapping_intent is None or mapping_intent == intent:
                mapping_type = requested_slot_mapping["type"]

                if mapping_type == "from_entity":
                    # list is used to cover the case of list slot type
                    value = list(tracker.get_latest_entity_values(
                                    requested_slot_mapping.get("entity")))
                    if len(value) == 1:
                        value = value[0]
                elif mapping_type == "from_intent":
                    value = requested_slot_mapping.get("value")
                elif mapping_type == "from_text":
                    value = tracker.latest_message.get("text")
                else:
                    raise ValueError(
                            'Provided slot mapping type '
                            'is not supported')

                if value:
                    logger.debug("Successfully extracted '{}' "
                                 "for requested slot '{}'"
                                 "".format(value, slot_to_fill))
                    return {slot_to_fill: value}

        logger.debug("Failed to extract requested slot '{}'"
                     "".format(slot_to_fill))
        return {}

    # noinspection PyUnusedLocal
    def extract_other_slots(self,
                            dispatcher,  # type: CollectingDispatcher
                            tracker,  # type: Tracker
                            domain  # type: Dict[Text, Any]
                            ):
        # type: (...) -> Dict[Text: Any]
        """Extract the values of the other slots
            if they are set by corresponded entities from a user input
            else return None
        """
        slot_to_fill = tracker.get_slot(REQUESTED_SLOT)

        slot_values = {}
        for slot in self.required_slots(tracker):
            # look for other slots
            if slot != slot_to_fill:
                # list is used to cover the case of list slot type
                value = list(tracker.get_latest_entity_values(slot))
                if len(value) == 1:
                    value = value[0]

                if value:
                    logger.debug("Extracted '{}' "
                                 "for extra slot '{}'"
                                 "".format(value, slot))
                    slot_values[slot] = value

        return slot_values

    def validate(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """Validate extracted value of requested slot
            else reject to execute the form action

            Subclass this method to add custom validation and rejection logic
        """
        # extract other slots that were not requested
        # but set by corresponding entity
        slot_values = self.extract_other_slots(dispatcher, tracker, domain)

        # extract requested slot
        slot_to_fill = tracker.get_slot(REQUESTED_SLOT)
        if slot_to_fill:
            slot_values.update(self.extract_requested_slot(dispatcher,
                                                           tracker, domain))
            if not slot_values:
                # reject to execute the form action
                # if some slot was requested but nothing was extracted
                # it will allow other policies to predict another action
                raise ActionExecutionRejection(self.name(),
                                               "Failed to validate slot {0} "
                                               "with action {1}"
                                               "".format(slot_to_fill,
                                                         self.name()))

        # validation succeed, set slots to extracted values
        return [SlotSet(slot, value) for slot, value in slot_values.items()]

    # noinspection PyUnusedLocal
    def request_next_slot(self,
                          dispatcher,  # type: CollectingDispatcher
                          tracker,  # type: Tracker
                          domain  # type: Dict[Text, Any]
                          ):
        # type: (...) -> Optional[List[Dict]]
        """Request the next slot and utter template if needed,
            else return None"""

        for slot in self.required_slots(tracker):
            if self._should_request_slot(tracker, slot):
                logger.debug("Request next slot '{}'".format(slot))
                dispatcher.utter_template("utter_ask_{}".format(slot), tracker)
                return [SlotSet(REQUESTED_SLOT, slot)]

        logger.debug("No slots left to request")
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

        if tracker.active_form.get('name') is not None:
            logger.debug("The form '{}' is active"
                         "".format(tracker.active_form))
        else:
            logger.debug("There is no active form")

        if tracker.active_form.get('name') == self.name():
            return []
        else:
            logger.debug("Activate the form '{}'".format(self.name()))
            return [Form(self.name())]

    def _validate_if_required(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """Return a list of events from `self.validate(...)`
            if validation is required:
            - the form is active
            - the form is called after `action_listen`
            - form validation was not cancelled
        """
        if (tracker.latest_action_name == 'action_listen' and
                tracker.active_form.get('validate', True)):
            logger.debug("Validate user input")
            return self.validate(dispatcher, tracker, domain)
        else:
            logger.debug("Skip validation")
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
        logger.debug("Deactivating the form")
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

        # create temp tracker with populated slots from `validate` method
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
