# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
from typing import Text

from rasa_core_sdk import Action, InputValidationError
from rasa_core_sdk.events import SlotSet, FormActivated, FormDeactivated

logger = logging.getLogger(__name__)

# this slot is used to store information needed
# to do the form handling, needs to be part
# of the domain
REQUESTED_SLOT = "requested_slot"


class FormAction(Action):
    def name(self):
        # type: () -> Text
        """Unique identifier of this form action."""

        raise NotImplementedError

    RANDOMIZE = False

    @staticmethod
    def required_slots():
        raise NotImplementedError

    @staticmethod
    def should_request_slot(tracker, slot_name):
        existing_val = tracker.get_slot(slot_name)
        return existing_val is None

    def validate(self, tracker):
        # type: (Tracker) -> Dict[Text, Any]
        """"Validate the user input."""

        raise InputValidationError("validation not implemented")

    def activate_if_required(self, tracker):
        if tracker.active_form == self.name():
            return []
        else:
            return [FormActivated(self.name())]

    def get_requested_slot(self, tracker):
        events = []
        intent = tracker.latest_message["intent"].get("name")
        if intent == "extracted_slot":
            for slot in tracker.latest_message["slots"]:
                events.append(SlotSet(slot['name'], slot['value']))

        return events

    def run(self, dispatcher, tracker, domain):

        events = self.get_requested_slot(tracker)
        temp_tracker = tracker.copy()
        for e in events:
            temp_tracker.slots[e["name"]] = e["value"]
        for slot in self.required_slots():
            if self.should_request_slot(temp_tracker, slot):

                dispatcher.utter_template(
                        "utter_ask_{}".format(slot),
                        tracker)

                events.append(SlotSet(REQUESTED_SLOT, slot))

                return events + self.activate_if_required(tracker)

        # there is nothing more to request, so we can submit
        events_from_submit = self.submit(dispatcher, temp_tracker, domain) or []

        return events + events_from_submit + [FormDeactivated()]

    def submit(self, dispatcher, tracker, domain):
        raise NotImplementedError(
                "a form action must implement a submit method")
