# -*- coding: utf-8 -*-
from typing import Text, Dict, Any, List, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.knowledge_base.storage import (
    Attribute,
    KnowledgeBase,
    SCHEMA_KEYS_ATTRIBUTES,
    SCHEMA_KEYS_REPRESENTATION,
    SCHEMA_KEYS_KEY,
)


# TODO
# - can we somehow set the knowledge base without inheriting the KB action?
# - can we automatically set the slots for the action if they are not set?
# - documentation
# - should we hide the slots that are only set via the action (listed items) in the
# tracker somehow?
# - test, test, test


class ActionKnowledgeBase(Action):
    """
    Abstract knowledge base action that can be inherited to create custom actions
    that are able to interact with the knowledge base.
    """

    def __init__(self, knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base

    def name(self):
        raise NotImplementedError("An action must implement a name")

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        raise NotImplementedError("An action must implement its run method")


class ActionQueryKnowledgeBase(ActionKnowledgeBase):
    """
    Action that queries the knowledge base for entities and attributes of an entity.
    The action needs to be inherited and the knowledge base needs to be set.
    In order to actually query the knowledge base you need to:
    - create your knowledge base
    - add mandatory slots to the domain file: 'entity_type', 'attribute', 'mention'
    - create an intent that triggers this action
    - mark all needed entities in the NLU data, such as 'entity_type'
    - create a story that includes this action
    - add created intent and action to domain file
    """

    def __init__(self, knowledge_base: KnowledgeBase):
        super().__init__(knowledge_base)

    def name(self):
        raise NotImplementedError("An action must implement a name.")

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        entity_type = tracker.get_slot("entity_type")
        attribute = tracker.get_slot("attribute")

        if not entity_type:
            dispatcher.utter_message(
                "Sorry, I did not get that. Can you please rephrase?"
            )
            return []

        if not attribute:
            return self._query_entities(dispatcher, tracker)
        elif attribute:
            return self._query_attribute(dispatcher, tracker)

        dispatcher.utter_message("Sorry, I did not get that. Can you please rephrase?")
        return []

    def _query_entities(
        self, dispatcher: CollectingDispatcher, tracker: Tracker
    ) -> List[Dict[Text, Any]]:
        """
        Queries the knowledge base for entities of the requested entity type and
        outputs those to the user.

        :param dispatcher: the dispatcher
        :param tracker: the tracker

        :return: list of slots
        """
        entity_type = tracker.get_slot("entity_type")

        attributes = self._get_attributes_of_entity(entity_type, tracker)
        entities = self.knowledge_base.get_entities(entity_type, attributes)

        if not entities:
            dispatcher.utter_message(
                "I could not find any entities of type '{}'.".format(entity_type)
            )
            return []

        representation_function = self.knowledge_base.schema[entity_type][
            SCHEMA_KEYS_REPRESENTATION
        ]

        dispatcher.utter_message(
            "Found the following entities of type '{}':".format(entity_type)
        )
        for i, e in enumerate(entities):
            dispatcher.utter_message("{}: {}".format(i + 1, representation_function(e)))

        key_attribute = self.knowledge_base.schema[entity_type][SCHEMA_KEYS_KEY]

        last_entity = None if len(entities) > 1 else entities[0][key_attribute]

        slots = [
            SlotSet("entity_type", entity_type),
            SlotSet("mention", None),
            SlotSet("attribute", None),
            SlotSet("knowledge_base_last_entity", last_entity),
            SlotSet("knowledge_base_last_entity_type", entity_type),
            SlotSet(
                "knowledge_base_entities",
                list(map(lambda e: e[key_attribute], entities)),
            ),
        ]

        return slots + self._reset_attribute_slots(entity_type, tracker)

    def _query_attribute(
        self, dispatcher: CollectingDispatcher, tracker: Tracker
    ) -> List[Dict[Text, Any]]:
        """
        Queries the knowledge base for the value of the requested attribute of the
        mentioned entity and outputs it to the user.

        :param dispatcher: the dispatcher
        :param tracker: the tracker

        :return: list of slots
        """
        entity_type = tracker.get_slot("entity_type")
        attribute = tracker.get_slot("attribute")

        entity = self._get_entity(tracker)

        if not entity or not attribute:
            dispatcher.utter_message(
                "Sorry, I did not get that. Can you please rephrase?"
            )

            slots = [SlotSet("mention", None)]
            return slots + self._reset_attribute_slots(entity_type, tracker)

        value = self.knowledge_base.get_attribute_of(entity_type, entity, attribute)

        # utter response
        if value:
            dispatcher.utter_message(
                "'{}' has the value '{}' for attribute '{}'.".format(
                    entity, value, attribute
                )
            )
        else:
            dispatcher.utter_message(
                "Did not found a valid value for attribute '{}' for entity '{}'.".format(
                    attribute, entity
                )
            )

        slots = [
            SlotSet("entity_type", entity_type),
            SlotSet("mention", None),
            SlotSet("knowledge_base_last_entity", entity),
            SlotSet("knowledge_base_last_entity_type", entity_type),
        ]

        return slots + self._reset_attribute_slots(entity_type, tracker)

    def _get_entity(self, tracker: Tracker) -> Text:
        """
        Get the name of the entity the user referred to. Either the NER detected the
        entity and stored its name in the corresponding slot or the user referred to
        the entity by any kind of mention, such as "first one" or "it".

        :param tracker: Tracker

        :return: the name of the actual entity (value of key attribute in the knowledge base)
        """
        mention = tracker.get_slot("mention")
        entity_type = tracker.get_slot("entity_type")

        if mention:
            return self._resolve_mention(tracker)

        # check whether the user referred to the entity by its name
        entity_name = tracker.get_slot(entity_type)
        if entity_name:
            return entity_name

        # if no explicit mention was found, we assume the user just refers to the last
        # entity mentioned in the conversation
        return tracker.get_slot("knowledge_base_last_entity")

    def _resolve_mention(self, tracker: Tracker) -> Optional[Text]:
        """
        Resolves a mention of an entity, such as first, to the actual entity.
        If multiple entities are listed during the conversation, the entities
        are stored in the slot 'knowledge_base_entities' as a list. We resolve the
        mention, such as first, to the list index and retrieve the actual entity.
        If the mention is not an ordinal mention, but some other reference, we just
        assume the user is referring to the last mentioned entity in the conversation.

        :param tracker: tracker

        :return: name of the actually entity
        """

        mention = tracker.get_slot("mention")
        listed_items = tracker.get_slot("knowledge_base_entities")
        last_entity = tracker.get_slot("knowledge_base_last_entity")
        last_entity_type = tracker.get_slot("knowledge_base_last_entity_type")
        current_entity_type = tracker.get_slot("entity_type")

        if not mention:
            return None

        if listed_items and mention in self.knowledge_base.ordinal_mention_mapping:
            idx_function = self.knowledge_base.ordinal_mention_mapping[mention]
            return idx_function(listed_items)

        # NOTE:
        # for now we just assume, that if the user refers to an entity, for
        # example via "it" or "that restaurant". he actually refers to the last
        # entity that was detected.
        if current_entity_type == last_entity_type:
            return last_entity

    def _to_str(self, entity_type: Text, entity: Dict[Text, Any]) -> Text:
        """
        Converts an entity to its string representation using the lambda function
        defined in the schema

        :param entity_type: the entity type
        :param entity: the entity with all its attributes

        :return: a string that represents the entity
        """
        representation_func = self.knowledge_base.schema[entity_type][SCHEMA_KEYS_REPRESENTATION]
        return representation_func(entity)

    def _get_attributes_of_entity(
        self, entity_type: Text, tracker: Tracker
    ) -> List[Attribute]:
        """
        Checks if the NER found any value for all attributes of the given entity type.

        :param entity_type: the entity type
        :param tracker: the tracker

        :return: a list of attributes
        """
        attributes = []

        if entity_type not in self.knowledge_base.schema:
            return attributes

        for attr in self.knowledge_base.schema[entity_type][SCHEMA_KEYS_ATTRIBUTES]:
            attr_val = tracker.get_slot(attr)
            if attr_val is not None:
                attributes.append(Attribute(attr, attr_val))

        return attributes

    def _reset_attribute_slots(
        self, entity_type: Text, tracker: Tracker
    ) -> List[SlotSet]:
        """
        Reset all attribute slots of the current entity type.

        :param entity_type: the entity type
        :param tracker: the tracker

        :return: list of reset slots
        """
        slots = []

        if entity_type not in self.knowledge_base.schema:
            return slots

        for attr in self.knowledge_base.schema[entity_type][SCHEMA_KEYS_ATTRIBUTES]:
            attr_val = tracker.get_slot(attr)
            if attr_val is not None:
                slots.append(SlotSet(attr, None))

        return slots
