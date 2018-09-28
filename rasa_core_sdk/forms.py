# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import typing
from typing import Dict, Text, Any, List, Union

from rasa_core_sdk import Action, ActionExecutionError
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
    def required_slots():
        # type: () -> List[Text]
        """A list of required slots that the form has to fill"""

        raise NotImplementedError("A form must implement required slots "
                                  "that it has to fill")

    def slot_mapping(self):
        # type: () -> Dict[Text: Union[Text, List[Text]]]
        """A dictionary to map required slots to extracted entities"""

        return dict(zip(self.required_slots(), self.required_slots()))

    # noinspection PyUnusedLocal
    def validate(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """"Validate the user input else return an error"""
        slot_to_fill = tracker.slots[REQUESTED_SLOT]

        # map requested_slot to entity
        required_entities = self.slot_mapping().get(slot_to_fill)

        if required_entities:
            if isinstance(required_entities, str):
                required_entities = [required_entities]

            for e in tracker.latest_message["entities"]:
                if e.get("entity") in required_entities:
                    return [SlotSet(slot_to_fill, e['value'])]

        raise ActionExecutionError("Failed to validate slot {0} "
                                   "with action {1}"
                                   "".format(slot_to_fill, self.name()),
                                   self.name())

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

    def _validate_if_required(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """Return a list of events from `self.validate`
            if validation is required:
            - the form is active
            - the form is called after `action_listen`
        """
        if (tracker.active_form == self.name() and
                tracker.latest_action_name == 'action_listen'):
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

        # request next slot
        for slot in self.required_slots():
            if self._should_request_slot(temp_tracker, slot):

                dispatcher.utter_template("utter_ask_{}".format(slot), tracker)

                events.append(SlotSet(REQUESTED_SLOT, slot))

                return events

        # there is nothing more to request, so we can submit
        events.extend(self.submit(dispatcher, temp_tracker, domain))
        # deactivate the form after submission
        events.extend(self._deactivate())

        return events

    def __str__(self):
        return "Form('{}')".format(self.name())
