import logging
import typing
from enum import Enum
from typing import Dict, Text, Any, List, Union, Optional

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:  # pragma: no cover
    from rasa_sdk import Tracker
    from rasa_sdk.types import DomainDict


class SlotMapping(Enum):
    """Defines the available slot mappings."""

    FROM_ENTITY = 0
    FROM_INTENT = 1
    FROM_TRIGGER_INTENT = 2
    FROM_TEXT = 3
    CUSTOM = 4

    def __str__(self) -> Text:
        """Returns a string representation of the object."""
        return self.name.lower()

    @staticmethod
    def to_list(x: Optional[Any]) -> List[Any]:
        """Convert object to a list if it isn't."""
        if x is None:
            x = []
        elif not isinstance(x, list):
            x = [x]

        return x

    @staticmethod
    def from_entity(
        entity: Text,
        intent: Optional[Union[Text, List[Text]]] = None,
        not_intent: Optional[Union[Text, List[Text]]] = None,
        role: Optional[Text] = None,
        group: Optional[Text] = None,
    ) -> Dict[Text, Any]:
        """A dictionary for slot mapping to extract slot value.

        From:
        - an extracted entity
        - conditioned on
            - intent if it is not None
            - not_intent if it is not None,
                meaning user intent should not be this intent
            - role if it is not None
            - group if it is not None
        """
        intent, not_intent = (
            SlotMapping.to_list(intent),
            SlotMapping.to_list(not_intent),
        )

        return {
            "type": str(SlotMapping.FROM_ENTITY),
            "entity": entity,
            "intent": intent,
            "not_intent": not_intent,
            "role": role,
            "group": group,
        }

    @staticmethod
    def from_trigger_intent(
        value: Any,
        intent: Optional[Union[Text, List[Text]]] = None,
        not_intent: Optional[Union[Text, List[Text]]] = None,
    ) -> Dict[Text, Any]:
        """A dictionary for slot mapping to extract slot value.

        From:
        - trigger_intent: value pair
        - conditioned on
            - intent if it is not None
            - not_intent if it is not None,
                meaning user intent should not be this intent

        Only used on form activation.
        """
        intent, not_intent = (
            SlotMapping.to_list(intent),
            SlotMapping.to_list(not_intent),
        )

        return {
            "type": str(SlotMapping.FROM_TRIGGER_INTENT),
            "value": value,
            "intent": intent,
            "not_intent": not_intent,
        }

    @staticmethod
    def from_intent(
        value: Any,
        intent: Optional[Union[Text, List[Text]]] = None,
        not_intent: Optional[Union[Text, List[Text]]] = None,
    ) -> Dict[Text, Any]:
        """A dictionary for slot mapping to extract slot value.

        From:
        - intent: value pair
        - conditioned on
            - intent if it is not None
            - not_intent if it is not None,
                meaning user intent should not be this intent
        """
        intent, not_intent = (
            SlotMapping.to_list(intent),
            SlotMapping.to_list(not_intent),
        )

        return {
            "type": str(SlotMapping.FROM_INTENT),
            "value": value,
            "intent": intent,
            "not_intent": not_intent,
        }

    @staticmethod
    def from_text(
        intent: Optional[Union[Text, List[Text]]] = None,
        not_intent: Optional[Union[Text, List[Text]]] = None,
    ) -> Dict[Text, Any]:
        """A dictionary for slot mapping to extract slot value.

        From:
        - a whole message
        - conditioned on
            - intent if it is not None
            - not_intent if it is not None,
                meaning user intent should not be this intent
        """
        intent, not_intent = (
            SlotMapping.to_list(intent),
            SlotMapping.to_list(not_intent),
        )

        return {
            "type": str(SlotMapping.FROM_TEXT),
            "intent": intent,
            "not_intent": not_intent,
        }

    @staticmethod
    def intent_is_desired(
        mapping: Dict[Text, Any],
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> bool:
        """Check whether user intent matches intent conditions."""
        mapping_intents = SlotMapping.to_list(mapping.get("intent", []))
        mapping_not_intents = SlotMapping.to_list(mapping.get("not_intent", []))

        active_loop_name = tracker.active_loop_name
        if active_loop_name:
            mapping_not_intents = (
                mapping_not_intents
                + SlotMapping._get_ignored_intents(mapping, domain, active_loop_name)
            )

        intent = tracker.latest_message.get("intent", {}).get("name")

        intent_not_excluded = not mapping_intents and intent not in mapping_not_intents

        return intent_not_excluded or intent in mapping_intents

    @staticmethod
    def entity_is_desired(
        mapping: Dict[Text, Any],
        tracker: "Tracker",
    ) -> bool:
        """Checks whether slot should be filled by an entity in the input or not.

        Args:
            mapping: Slot mapping.
            tracker: The tracker.

        Returns:
            True, if slot should be filled, false otherwise.
        """
        slot_fulfils_entity_mapping = False
        extracted_entities = tracker.latest_message.get("entities", [])

        for entity in extracted_entities:
            if (
                mapping.get("entity") == entity["entity"]
                and mapping.get("role") == entity.get("role")
                and mapping.get("group") == entity.get("group")
            ):
                matching_values = tracker.get_latest_entity_values(
                    mapping.get("entity", ""),
                    mapping.get("role"),
                    mapping.get("group"),
                )
                slot_fulfils_entity_mapping = matching_values is not None
                break

        return slot_fulfils_entity_mapping

    @staticmethod
    def _get_ignored_intents(
        mapping: Dict[Text, Any],
        domain: "DomainDict",
        active_loop_name: Text,
    ) -> List[Text]:
        mapping_conditions = mapping.get("conditions")
        active_loop_match = False
        ignored_intents = []

        if mapping_conditions:
            for condition in mapping_conditions:
                if condition.get("active_loop") == active_loop_name:
                    active_loop_match = True
                    break

        if active_loop_match:
            form_ignored_intents = domain.get("forms", {})[active_loop_name].get(
                "ignored_intents", []
            )
            if not isinstance(form_ignored_intents, list):
                ignored_intents = [form_ignored_intents]
            else:
                ignored_intents = form_ignored_intents

        return ignored_intents
