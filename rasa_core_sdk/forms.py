# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import random
from typing import List, Text

from rasa_core_sdk import Action, Tracker
from rasa_core_sdk.events import SlotSet, FormListen, EventType
from rasa_core.constants import FORM_ACTION_NAME

logger = logging.getLogger(__name__)

# this slot is used to store information needed
# to do the form handling, needs to be part
# of the domain
FORM_SLOT_NAME = "requested_slot"


class FormAction(Action):
    def name(self):
        return FORM_ACTION_NAME

    def run(self, dispatcher, tracker, domain, executor):
        form = executor.forms[tracker.active_form]
        next_action = form.next_action(tracker)
        if next_action in domain['templates'].keys():
            dispatcher.utter_template(next_action, tracker)
            return []
        elif next_action == 'action_listen':
            return [FormListen()]
        else:
            return executor.actions[next_action](dispatcher, tracker, domain, executor)


class Form(object):
    """Next action to be taken in response to a dialogue state."""

    def next_action(self, tracker):
        # type: (DialogueStateTracker) -> List[Event]
        """
        Choose an action idx given the current state of the tracker and the form.

        Args:
            tracker (DialogueStateTracker): the state tracker for the current user.
                You can access slot values using ``tracker.get_slot(slot_name)``
                and the most recent user message is ``tracker.latest_message.text``.
            domain (Domain): the bot's domain

        Returns:
            idx: the index of the next planned action in the domain

        """

        raise NotImplementedError

    def __str__(self):
        return "Form('{}')".format(self.name)


class SimpleForm(Form):
    def __init__(self, name, fields, finish_action, breakout_intents=None, chitchat_intents=None, details_intent=None, rules=None, max_turns=10, failure_action=None):
        self.name = name
        self.fields = fields
        self.required_slots = list(self.fields.keys())
        self.breakout_intents = breakout_intents
        self.chitchat_intents = chitchat_intents
        self.finish_action = finish_action
        self.details_intent = details_intent
        self._validate_slots()
        self.rules_yaml = rules
        self.rules = self._process_rules(self.rules_yaml)

        self.last_question = None
        self.queue = []
        self.current_required = self.required_slots
        self.max_turns = max_turns
        self.current_failures = 0
        if failure_action is None:
            self.failure_action = finish_action
        else:
            self.failure_action = failure_action

    def _validate_slots(self):
        for slot, values in self.fields.items():
            if 'ask_utt' not in list(values.keys()):
                logger.error('ask_utt not found for {} in form {}. An utterance is required to ask for a certain slot'.format(slot, self.name))
            if 'clarify_utt' not in list(values.keys()) and self.details_intent not in [None, []]:
                logger.warning('clarify_utt not found for {} in form {}, even though {} is listed as a details intent.'.format(slot, self.name, self.details_intent))

    @staticmethod
    def _process_rules(rules):
        rule_dict = {}
        for slot, values in rules.items():
            for value, rules in values.items():
                rule_dict[(slot, value)] = (rules.get('need'), rules.get('lose'))
        return rule_dict

    def _update_requirements(self, tracker):
        #type: (DialogueStateTracker)
        if self.rules is None:
            return
        all_add, all_take = [], []
        for slot_tuple in list(tracker.current_slot_values().items()):
            if slot_tuple in self.rules.keys():
                add, take = self.rules[slot_tuple]
                if add is not None:
                    all_add.extend(add)
                if take is not None:
                    all_take.extend(take)
        self.current_required = self._prioritise_questions(list(set(self.required_slots+all_add)-set(all_take)))

    def _prioritise_questions(self, slots):
        #type: (list) -> (list)
        return sorted(slots, key=lambda l: self.fields[l].get('priority', 1E5))

    def check_unfilled_slots(self, tracker):
        #type: (DialogueStateTracker) -> ([str])
        current_filled_slots = [key for key, value in tracker.current_slot_values().items() if value is not None]
        still_to_ask = list(set(self.current_required) - set(current_filled_slots))
        still_to_ask = self._prioritise_questions(still_to_ask)
        for slot in still_to_ask:
            if slot not in tracker.current_slot_values().keys():
                logger.warning("Slot {} not found in tracker, did you include it in your domain file?".format(slot))
        return still_to_ask

    def _run_through_queue(self):
        # take next action in the queue
        if self.queue == []:
            return None
        else:
            return self.queue.pop(0)

    def _question_queue(self, question):
        # the default question queue will ask for the slot and then listen
        queue = [self.fields[question]['ask_utt'], 'action_listen']
        if 'follow_up_action' in self.fields[self.last_question].keys():
            queue.append(self.fields[self.last_question]['follow_up_action'])
        return queue

    def _details_queue(self, intent, tracker):
        # details will perform the clarify utterance and then ask the question again
        self.queue = [self.fields[self.last_question]['clarify_utt']]
        self.queue.extend(self._question_queue(self.last_question))

    def _chitchat_queue(self, intent, tracker):
        # chitchat queue will perform the chitchat action and return to the last question
        self.queue = [self.chitchat_intents[intent]]
        self.queue.extend(self._question_queue(self.last_question))

    def _exit_queue(self, intent, tracker):
        # If the exit dict is called, the form will be deactivated
        self.queue = [self.breakout_intents[intent]]

    def _decide_next_question(self, still_to_ask, tracker):
        # in the default setting this will ask the first (highest priority) slot, but can be overridden
        return still_to_ask[0]

    def next_action(self, tracker):
        # type: (DialogueStateTracker) -> int

        out = self._run_through_queue()
        if out is not None:
            # There are still actions in the queue, do the next one
            return out

        self._update_requirements(tracker)
        still_to_ask = self.check_unfilled_slots(tracker)

        if len(still_to_ask) == 0:
            # if all the slots have been filled then queue finish actions
            self.queue = [self.finish_action]
            return self._run_through_queue()

        self.current_failures += 1
        if self.current_failures > self.max_turns:
            self.queue = [self.failure_action]
            return self._run_through_queue()

        intent = tracker.latest_message['intent']['name']

        if intent in self.breakout_intents.keys():
            # actions in this dict should deactivate this form in the tracker
            self._exit_queue(intent, tracker)
            return self._run_through_queue()

        elif intent in self.chitchat_intents.keys():
            self._chitchat_queue(intent, tracker)
            return self._run_through_queue()

        elif self.details_intent and intent == self.details_intent:
            self._details_queue(intent, tracker)
            return self._run_through_queue()

        # otherwise just ask to fill slots
        self.last_question = self._decide_next_question(still_to_ask, tracker)
        self.queue = self._question_queue(self.last_question)
        return self._run_through_queue()
