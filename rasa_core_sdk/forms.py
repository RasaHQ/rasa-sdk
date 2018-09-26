# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
from typing import Text

from rasa_core_sdk import Action
from rasa_core_sdk.events import SlotSet, Form
from rasa_core.actions.action import ActionExecutionError

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

    def validate(self, dispatcher, tracker):
        # type: (Tracker) -> Dict[Text, Any]
        """"Validate the user input."""

        events = []
        entities = tracker.latest_message["entities"]

        for e in entities:
            if e.get("entity") == tracker.slots[REQUESTED_SLOT]:
                events.append(SlotSet(e['entity'], e['value']))
        if events:
            return events
        else:
            raise ActionExecutionError("Failed to validate slot {0} with "
                                       "action {1}".format(
                                                tracker.slots[REQUESTED_SLOT],
                                                self.name()), self.name())

    def activate_if_required(self, tracker):
        if tracker.active_form == self.name():
            return []
        else:
            return [Form(self.name())]

    def run(self, dispatcher, tracker, domain):

        if tracker.active_form == self.name() and tracker.latest_action_name == 'action_listen':
            events = self.validate(dispatcher, tracker)
        else:
            events = []

        temp_tracker = tracker.copy()
        for e in events:
            temp_tracker.slots[e["name"]] = e["value"]
        for slot in self.required_slots():
            if self.should_request_slot(temp_tracker, slot):

                dispatcher.utter_template("utter_ask_{}".format(slot), tracker)

                events.append(SlotSet(REQUESTED_SLOT, slot))

                return self.activate_if_required(tracker) + events

        # there is nothing more to request, so we can submit
        events_from_submit = self.submit(dispatcher, temp_tracker, domain) or []

        return events + events_from_submit + [SlotSet(REQUESTED_SLOT, None), Form(None)]

    def submit(self, dispatcher, tracker, domain):
        raise NotImplementedError(
                "a form action must implement a submit method")
