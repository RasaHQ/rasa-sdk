# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import typing
from typing import Dict, Text, Any, List, Union, Optional, Tuple

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
        """A list of required slots that the form has to fill.

        Use `tracker` to request different list of slots
        depending on the state of the dialogue
        """

        raise NotImplementedError(
            "A form must implement required slots that it has to fill"
        )

    def from_entity(
        self,
        entity,  # type: Text
        intent=None,  # type: Optional[Union[Text, List[Text]]]
        not_intent=None,  # type: Optional[Union[Text, List[Text]]]
    ):
        # type: (...) -> Dict[Text: Any]
        """A dictionary for slot mapping to extract slot value.

        From:
        - an extracted entity
        - conditioned on
            - intent if it is not None
            - not_intent if it is not None,
                meaning user intent should not be this intent
        """

        intent, not_intent = self._list_intents(intent, not_intent)

        return {
            "type": "from_entity",
            "entity": entity,
            "intent": intent,
            "not_intent": not_intent,
        }

    def from_trigger_intent(
        self,
        value,  # type: Any
        intent=None,  # type: Optional[Union[Text, List[Text]]]
        not_intent=None,  # type: Optional[Union[Text, List[Text]]]
    ):
        # type: (...) -> Dict[Text: Any]
        """A dictionary for slot mapping to extract slot value.

        From:
        - trigger_intent: value pair
        - conditioned on
            - intent if it is not None
            - not_intent if it is not None,
                meaning user intent should not be this intent

        Only used on form activation.
        """

        intent, not_intent = self._list_intents(intent, not_intent)

        return {
            "type": "from_trigger_intent",
            "value": value,
            "intent": intent,
            "not_intent": not_intent,
        }

    def from_intent(
        self,
        value,  # type: Any
        intent=None,  # type: Optional[Union[Text, List[Text]]]
        not_intent=None,  # type: Optional[Union[Text, List[Text]]]
    ):
        # type: (...) -> Dict[Text: Any]
        """A dictionary for slot mapping to extract slot value.

        From:
        - intent: value pair
        - conditioned on
            - intent if it is not None
            - not_intent if it is not None,
                meaning user intent should not be this intent
        """

        intent, not_intent = self._list_intents(intent, not_intent)

        return {
            "type": "from_intent",
            "value": value,
            "intent": intent,
            "not_intent": not_intent,
        }

    def from_text(
        self,
        intent=None,  # type: Optional[Union[Text, List[Text]]]
        not_intent=None,  # type: Optional[Union[Text, List[Text]]]
    ):
        # type: (...) -> Dict[Text: Any]
        """A dictionary for slot mapping to extract slot value.

        From:
        - a whole message
        - conditioned on
            - intent if it is not None
            - not_intent if it is not None,
                meaning user intent should not be this intent
        """

        intent, not_intent = self._list_intents(intent, not_intent)

        return {"type": "from_text", "intent": intent, "not_intent": not_intent}

    # noinspection PyMethodMayBeStatic
    def slot_mappings(self):
        # type: () -> Dict[Text: Union[Dict, List[Dict]]]
        """A dictionary to map required slots.

        Options:
        - an extracted entity
        - intent: value pairs
        - trigger_intent: value pairs
        - a whole message
        or a list of them, where the first match will be picked

        Empty dict is converted to a mapping of
        the slot to the extracted entity with the same name
        """

        return {}

    def get_mappings_for_slot(self, slot_to_fill):
        # type: (Text) -> List[Dict[Text: Any]]
        """Get mappings for requested slot.

        If None, map requested slot to an entity with the same name
        """

        requested_slot_mappings = self._to_list(
            self.slot_mappings().get(slot_to_fill, self.from_entity(slot_to_fill))
        )
        # check provided slot mappings
        for requested_slot_mapping in requested_slot_mappings:
            if (
                not isinstance(requested_slot_mapping, dict)
                or requested_slot_mapping.get("type") is None
            ):
                raise TypeError("Provided incompatible slot mapping")

        return requested_slot_mappings

    @staticmethod
    def intent_is_desired(requested_slot_mapping, tracker):
        # type: (Dict[Text: Any], Tracker) -> bool
        """Check whether user intent matches intent conditions"""

        mapping_intents = requested_slot_mapping.get("intent", [])
        mapping_not_intents = requested_slot_mapping.get("not_intent", [])
        intent = tracker.latest_message.get("intent", {}).get("name")

        intent_not_blacklisted = (
            not mapping_intents and intent not in mapping_not_intents
        )

        return intent_not_blacklisted or intent in mapping_intents

    @staticmethod
    def get_entity_value(name, tracker):
        # type: (Text, Tracker) -> Any
        """Extract entities for given name"""

        # list is used to cover the case of list slot type
        value = list(tracker.get_latest_entity_values(name))
        if len(value) == 0:
            value = None
        elif len(value) == 1:
            value = value[0]
        return value

    # noinspection PyUnusedLocal
    def extract_other_slots(
        self,
        dispatcher,  # type: CollectingDispatcher
        tracker,  # type: Tracker
        domain,  # type: Dict[Text, Any]
    ):
        # type: (...) -> Dict[Text: Any]
        """Extract the values of the other slots
            if they are set by corresponding entities from the user input
            else return None
        """
        slot_to_fill = tracker.get_slot(REQUESTED_SLOT)

        slot_values = {}
        for slot in self.required_slots(tracker):
            # look for other slots
            if slot != slot_to_fill:
                # list is used to cover the case of list slot type
                other_slot_mappings = self.get_mappings_for_slot(slot)

                for other_slot_mapping in other_slot_mappings:
                    intent = tracker.latest_message.get("intent", {}).get("name")
                    # check whether the slot should be filled
                    # by entity with the same name
                    should_fill_entity_slot = (
                        other_slot_mapping["type"] == "from_entity"
                        and other_slot_mapping.get("entity") == slot
                        and self.intent_is_desired(other_slot_mapping, tracker)
                    )
                    # check whether the slot should be
                    # filled from trigger intent mapping
                    should_fill_trigger_slot = (
                        tracker.active_form.get("name") != self.name()
                        and other_slot_mapping["type"] == "from_trigger_intent"
                        and self.intent_is_desired(other_slot_mapping, tracker)
                    )
                    if should_fill_entity_slot:
                        value = self.get_entity_value(slot, tracker)
                    elif should_fill_trigger_slot:
                        value = other_slot_mapping.get("value")
                    else:
                        value = None

                    if value is not None:
                        logger.debug(
                            "Extracted '{}' "
                            "for extra slot '{}'"
                            "".format(value, slot)
                        )
                        slot_values[slot] = value
                        # this slot is done, check  next
                        break

        return slot_values

    # noinspection PyUnusedLocal
    def extract_requested_slot(
        self,
        dispatcher,  # type: CollectingDispatcher
        tracker,  # type: Tracker
        domain,  # type: Dict[Text, Any]
    ):
        # type: (...) -> Dict[Text: Any]
        """Extract the value of requested slot from a user input
            else return None
        """
        slot_to_fill = tracker.get_slot(REQUESTED_SLOT)
        logger.debug("Trying to extract requested slot '{}' ...".format(slot_to_fill))

        # get mapping for requested slot
        requested_slot_mappings = self.get_mappings_for_slot(slot_to_fill)

        for requested_slot_mapping in requested_slot_mappings:
            logger.debug("Got mapping '{}'".format(requested_slot_mapping))

            if self.intent_is_desired(requested_slot_mapping, tracker):
                mapping_type = requested_slot_mapping["type"]

                if mapping_type == "from_entity":
                    value = self.get_entity_value(
                        requested_slot_mapping.get("entity"), tracker
                    )
                elif mapping_type == "from_intent":
                    value = requested_slot_mapping.get("value")
                elif mapping_type == "from_trigger_intent":
                    # from_trigger_intent is only used on form activation
                    continue
                elif mapping_type == "from_text":
                    value = tracker.latest_message.get("text")
                else:
                    raise ValueError("Provided slot mapping type is not supported")

                if value is not None:
                    logger.debug(
                        "Successfully extracted '{}' "
                        "for requested slot '{}'"
                        "".format(value, slot_to_fill)
                    )
                    return {slot_to_fill: value}

        logger.debug("Failed to extract requested slot '{}'".format(slot_to_fill))
        return {}

    def validate_slots(self, slot_dict, dispatcher, tracker, domain):
        # type: (Dict[Text, Any], CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """Validate slots using helper validation functions.

        Call validate_{slot} function for each slot, value pair to be validated.
        If this function is not implemented, set the slot to the value.
        """

        for slot, value in list(slot_dict.items()):
            validate_func = getattr(
                self, "validate_{}".format(slot), lambda *x: {slot: value}
            )
            validation_output = validate_func(value, dispatcher, tracker, domain)
            if not isinstance(validation_output, dict):
                logger.warning(
                    "Returning values in helper validation methods is deprecated. "
                    + "Your `validate_{}()` method should return ".format(slot)
                    + "a dict of {'slot_name': value} instead."
                )
                validation_output = {slot: validation_output}
            slot_dict.update(validation_output)

        # validation succeed, set slots to extracted values
        return [SlotSet(slot, value) for slot, value in slot_dict.items()]

    def validate(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """Extract and validate value of requested slot.

        If nothing was extracted reject execution of the form action.
        Subclass this method to add custom validation and rejection logic
        """

        # extract other slots that were not requested
        # but set by corresponding entity or trigger intent mapping
        slot_values = self.extract_other_slots(dispatcher, tracker, domain)

        # extract requested slot
        slot_to_fill = tracker.get_slot(REQUESTED_SLOT)
        if slot_to_fill:
            slot_values.update(self.extract_requested_slot(dispatcher, tracker, domain))

            if not slot_values:
                # reject to execute the form action
                # if some slot was requested but nothing was extracted
                # it will allow other policies to predict another action
                raise ActionExecutionRejection(
                    self.name(),
                    "Failed to extract slot {0} "
                    "with action {1}"
                    "".format(slot_to_fill, self.name()),
                )
        logger.debug("Validating extracted slots: {}".format(slot_values))
        return self.validate_slots(slot_values, dispatcher, tracker, domain)

    # noinspection PyUnusedLocal
    def request_next_slot(
        self,
        dispatcher,  # type: CollectingDispatcher
        tracker,  # type: Tracker
        domain,  # type: Dict[Text, Any]
    ):
        # type: (...) -> Optional[List[Dict]]
        """Request the next slot and utter template if needed,
            else return None"""

        for slot in self.required_slots(tracker):
            if self._should_request_slot(tracker, slot):
                logger.debug("Request next slot '{}'".format(slot))
                dispatcher.utter_template(
                    "utter_ask_{}".format(slot),
                    tracker,
                    silent_fail=False,
                    **tracker.slots
                )
                return [SlotSet(REQUESTED_SLOT, slot)]

        # no more required slots to fill
        return None

    def deactivate(self):
        # type: () -> List[Dict]
        """Return `Form` event with `None` as name to deactivate the form
            and reset the requested slot"""

        logger.debug("Deactivating the form '{}'".format(self.name()))
        return [Form(None), SlotSet(REQUESTED_SLOT, None)]

    def submit(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """Define what the form has to do
            after all required slots are filled"""

        raise NotImplementedError("A form must implement a submit method")

    # helpers
    @staticmethod
    def _to_list(x):
        # type: (Optional[Any]) -> List[Any]
        """Convert object to a list if it is not a list,
            None converted to empty list
        """
        if x is None:
            x = []
        elif not isinstance(x, list):
            x = [x]

        return x

    def _list_intents(
        self,
        intent=None,  # type: Optional[Union[Text, List[Text]]]
        not_intent=None,  # type: Optional[Union[Text, List[Text]]]
    ):
        # type: (...) -> Tuple[List[Text], List[Text]]
        """Check provided intent and not_intent"""
        if intent and not_intent:
            raise ValueError(
                "Providing  both intent '{}' and not_intent '{}' "
                "is not supported".format(intent, not_intent)
            )

        return self._to_list(intent), self._to_list(not_intent)

    def _log_form_slots(self, tracker):
        """Logs the values of all required slots before submitting the form."""

        req_slots = self.required_slots(tracker)
        slot_values = "\n".join(
            ["\t{}: {}".format(slot, tracker.get_slot(slot)) for slot in req_slots]
        )
        logger.debug(
            "No slots left to request, all required slots are filled:\n{}".format(
                slot_values
            )
        )

    def _activate_if_required(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """Activate form if the form is called for the first time.

        If activating, validate any required slots that were filled before
        form activation and return `Form` event with the name of the form, as well
        as any `SlotSet` events from validation of pre-filled slots.
        """

        if tracker.active_form.get("name") is not None:
            logger.debug("The form '{}' is active".format(tracker.active_form))
        else:
            logger.debug("There is no active form")

        if tracker.active_form.get("name") == self.name():
            return []
        else:
            logger.debug("Activated the form '{}'".format(self.name()))
            events = [Form(self.name())]

            # collect values of required slots filled before activation
            prefilled_slots = {}
            for slot_name in self.required_slots(tracker):
                if not self._should_request_slot(tracker, slot_name):
                    prefilled_slots[slot_name] = tracker.get_slot(slot_name)

            if prefilled_slots:
                logger.debug(
                    "Validating pre-filled required slots: {}".format(prefilled_slots)
                )
                events.extend(
                    self.validate_slots(prefilled_slots, dispatcher, tracker, domain)
                )
            else:
                logger.debug("No pre-filled required slots to validate.")

            return events

    def _validate_if_required(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """Return a list of events from `self.validate(...)`
            if validation is required:
            - the form is active
            - the form is called after `action_listen`
            - form validation was not cancelled
        """
        if tracker.latest_action_name == "action_listen" and tracker.active_form.get(
            "validate", True
        ):
            logger.debug("Validating user input '{}'".format(tracker.latest_message))
            return self.validate(dispatcher, tracker, domain)
        else:
            logger.debug("Skipping validation")
            return []

    @staticmethod
    def _should_request_slot(tracker, slot_name):
        # type: (Tracker, Text) -> bool
        """Check whether form action should request given slot"""

        return tracker.get_slot(slot_name) is None

    def run(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """Execute the side effects of this form.

        Steps:
        - activate if needed
        - validate user input if needed
        - set validated slots
        - utter_ask_{slot} template with the next required slot
        - submit the form if all required slots are set
        - deactivate the form
        """

        # activate the form
        events = self._activate_if_required(dispatcher, tracker, domain)
        # validate user input
        events.extend(self._validate_if_required(dispatcher, tracker, domain))
        # check that the form wasn't deactivated in validation
        if Form(None) not in events:

            # create temp tracker with populated slots from `validate` method
            temp_tracker = tracker.copy()
            for e in events:
                if e["event"] == "slot":
                    temp_tracker.slots[e["name"]] = e["value"]

            next_slot_events = self.request_next_slot(dispatcher, temp_tracker, domain)

            if next_slot_events is not None:
                # request next slot
                events.extend(next_slot_events)
            else:
                # there is nothing more to request, so we can submit
                self._log_form_slots(tracker)
                logger.debug("Submitting the form '{}'".format(self.name()))
                events.extend(self.submit(dispatcher, temp_tracker, domain))
                # deactivate the form after submission
                events.extend(self.deactivate())

        return events

    def __str__(self):
        return "FormAction('{}')".format(self.name())
