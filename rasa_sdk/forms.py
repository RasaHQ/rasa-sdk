import logging
import typing
import warnings
from typing import Dict, Text, Any, List, Optional

from abc import ABC
from rasa_sdk import utils
from rasa_sdk.events import SlotSet, EventType
from rasa_sdk.interfaces import Action

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:  # pragma: no cover
    from rasa_sdk import Tracker
    from rasa_sdk.executor import CollectingDispatcher
    from rasa_sdk.types import DomainDict

# this slot is used to store information needed
# to do the form handling
REQUESTED_SLOT = "requested_slot"

LOOP_INTERRUPTED_KEY = "is_interrupted"

ACTION_VALIDATE_SLOT_MAPPINGS = "action_validate_slot_mappings"


class ValidationAction(Action, ABC):
    """A helper class for slot validations and extractions of custom slots."""

    def name(self) -> Text:
        """Unique identifier of this simple action."""
        return ACTION_VALIDATE_SLOT_MAPPINGS

    async def run(
        self,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> List[EventType]:
        """Runs the custom actions. Please the docstring of the parent class."""
        extraction_events = await self.get_extraction_events(
            dispatcher, tracker, domain
        )
        tracker.add_slots(extraction_events)

        validation_events = await self._extract_validation_events(
            dispatcher, tracker, domain
        )

        # Validation events include events for extracted slots
        return validation_events

    async def _extract_validation_events(
        self,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> List[EventType]:
        validation_events = await self.get_validation_events(
            dispatcher, tracker, domain
        )
        tracker.add_slots(validation_events)

        return validation_events

    async def required_slots(
        self,
        domain_slots: List[Text],
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> List[Text]:
        """Returns slots which the validation action should fill.

        Args:
            domain_slots: Names of slots of this form which were mapped in
                the domain.
            dispatcher: the dispatcher which is used to
                send messages back to the user.
            tracker: the conversation tracker for the current user.
            domain: the bot's domain.

        Returns:
            A list of slot names.
        """
        return domain_slots

    async def get_extraction_events(
        self,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> List[EventType]:
        """Extracts custom slots using available `extract_<slot name>` methods.

        Uses the information from `self.required_slots` to gather which slots should
        be extracted.

        Args:
            dispatcher: the dispatcher which is used to
                send messages back to the user. Use
                `dispatcher.utter_message()` for sending messages.
            tracker: the state tracker for the current
                user. You can access slot values using
                `tracker.get_slot(slot_name)`, the most recent user message
                is `tracker.latest_message.text` and any other
                `rasa_sdk.Tracker` property.
            domain: the bot's domain.

        Returns:
            `SlotSet` for any extracted slots.
        """
        custom_slots = {}
        slots_to_extract = await self.required_slots(
            self.domain_slots(domain), dispatcher, tracker, domain
        )

        for slot in slots_to_extract:
            extraction_output = await self._extract_slot(
                slot, dispatcher, tracker, domain
            )
            custom_slots.update(extraction_output)
            # for sequential consistency, also update tracker
            # to make changes visible to subsequent extract_{slot_name}
            tracker.slots.update(extraction_output)

        return [SlotSet(slot, value) for slot, value in custom_slots.items()]

    async def get_validation_events(
        self,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> List[EventType]:
        """Validate slots by calling a validation function for each slot.

        Args:
            dispatcher: the dispatcher which is used to
                send messages back to the user.
            tracker: the conversation tracker for the current user.
            domain: the bot's domain.

        Returns:
            `SlotSet` events for every validated slot.
        """
        slots_to_validate = await self.required_slots(
            self.domain_slots(domain), dispatcher, tracker, domain
        )
        slots: Dict[Text, Any] = tracker.slots_to_validate()

        for slot_name, slot_value in list(slots.items()):
            if slot_name not in slots_to_validate:
                slots.pop(slot_name)
                continue

            method_name = f"validate_{slot_name.replace('-','_')}"
            validate_method = getattr(self, method_name, None)

            if not validate_method:
                logger.warning(
                    f"Skipping validation for `{slot_name}`: there is no validation "
                    f"method specified."
                )
                continue

            validation_output = await utils.call_potential_coroutine(
                validate_method(slot_value, dispatcher, tracker, domain)
            )

            if isinstance(validation_output, dict):
                slots.update(validation_output)
                # for sequential consistency, also update tracker
                # to make changes visible to subsequent validate_{slot_name}
                tracker.slots.update(validation_output)
            else:
                warnings.warn(
                    f"Cannot validate `{slot_name}`: make sure the validation method "
                    f"returns the correct output."
                )

        return [SlotSet(slot, value) for slot, value in slots.items()]

    @staticmethod
    def _is_mapped_to_form(slot_value: Dict[Text, Any]) -> bool:
        mappings = slot_value.get("mappings")
        if not mappings:
            return False

        for mapping in mappings:
            mapping_conditions = mapping.get("conditions", [])
            for condition in mapping_conditions:
                if condition.get("active_loop"):
                    return True

        return False

    def global_slots(self, domain: "DomainDict") -> List[Text]:
        """Returns all slots that contain no form condition."""
        all_slots = domain.get("slots", {})
        return [k for k, v in all_slots.items() if not self._is_mapped_to_form(v)]

    def domain_slots(self, domain: "DomainDict") -> List[Text]:
        """Returns slots which were mapped in the domain.

        Args:
            domain: The current domain.

        Returns:
            Slot names mapped in the domain which do not include
            a mapping with an active loop condition.
        """
        return self.global_slots(domain)

    async def _extract_slot(
        self,
        slot_name: Text,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> Dict[Text, Any]:
        method_name = f"extract_{slot_name.replace('-', '_')}"

        slot_in_domain = slot_name in self.domain_slots(domain)
        extract_method = getattr(self, method_name, None)

        if not extract_method:
            if not slot_in_domain:
                warnings.warn(
                    f"No method '{method_name}' found for slot "
                    f"'{slot_name}'. Skipping extraction for this slot."
                )
            return {}

        extracted = await utils.call_potential_coroutine(
            extract_method(dispatcher, tracker, domain)
        )

        if isinstance(extracted, dict):
            return extracted

        warnings.warn(
            f"Cannot extract `{slot_name}`: make sure the extract method "
            f"returns the correct output."
        )
        return {}


class FormValidationAction(ValidationAction, ABC):
    """A helper class for slot validations and extractions of custom slots in forms."""

    def name(self) -> Text:
        """Unique identifier of this simple action."""
        raise NotImplementedError("An action must implement a name")

    def form_name(self) -> Text:
        """Returns the form's name."""
        return self.name().replace("validate_", "", 1)

    async def _extract_validation_events(
        self,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> List[EventType]:
        validation_events = await self.get_validation_events(
            dispatcher, tracker, domain
        )
        tracker.add_slots(validation_events)

        next_slot = await self.next_requested_slot(dispatcher, tracker, domain)
        if next_slot:
            validation_events.append(next_slot)

        return validation_events

    def domain_slots(self, domain: "DomainDict") -> List[Text]:
        """Returns slots which were mapped in the domain.

        Args:
            domain: The current domain.

        Returns:
            Slot names which should be filled by the form. By default it
            returns the slot names which are listed for this form in the domain
            and use predefined mappings.
        """
        form = domain.get("forms", {}).get(self.form_name(), {})
        if "required_slots" in form:
            return form.get("required_slots", [])
        return []

    async def next_requested_slot(
        self,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> Optional[EventType]:
        """Sets the next slot which should be requested.

        Skips setting the next requested slot in case `missing_slots` was not
        overridden.

        Args:
            dispatcher: the dispatcher which is used to
                send messages back to the user.
            tracker: the conversation tracker for the current user.
            domain: the bot's domain.

        Returns:
            `None` in case `missing_slots` was not overridden and returns `None`.
            Otherwise returns a `SlotSet` event for the next slot to be requested.
            If the `SlotSet` event sets `requested_slot` to `None`, the form will be
            deactivated.
        """
        required_slots = await self.required_slots(
            self.domain_slots(domain), dispatcher, tracker, domain
        )
        if required_slots == self.domain_slots(domain):
            # If users didn't override `required_slots` then we'll let the `FormAction`
            # within Rasa Open Source request the next slot.
            return None

        missing_slots = (
            slot_name
            for slot_name in required_slots
            if tracker.slots.get(slot_name) is None
        )

        return SlotSet(REQUESTED_SLOT, next(missing_slots, None))
