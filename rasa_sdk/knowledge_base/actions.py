# -*- coding: utf-8 -*-
from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from rasa_sdk.knowledge_base.storage import (
    SCHEMA_KEYS_ATTRIBUTES,
    SCHEMA_KEYS_REPRESENTATION,
    SCHEMA_KEYS_KEY,
)


SLOT_MENTION = "mention"
SLOT_ENTITY_TYPE = "entity_type"
SLOT_ATTRIBUTE = "attribute"
SLOT_LISTED_ITEMS = "knowledge_base_listed_items"
SLOT_LAST_ENTITY = "knowledge_base_last_entity"
SLOT_LAST_ENTITY_TYPE = "knowledge_base_last_entity_type"


class ActionKnowledgeBase(Action):
    """
    Abstract knowledge base action that can be inherited to create custom actions
    that are able to interact with the knowledge base.
    """

    def __init__(self, knowledge_base):
        self.knowledge_base = knowledge_base

    def _get_entity(self, tracker):
        """
        Get the name of the entity the user referred to. Either the NER detected the
        entity and stored its name in the corresponding slot or the user referred to
        the entity by any kind of mention, such as "first one" or "it".

        Args:
            tracker: the tracker

        Returns: the name of the actual entity (value of key attribute in the knowledge base)
        """
        mention = tracker.get_slot(SLOT_MENTION)
        entity_type = tracker.get_slot(SLOT_ENTITY_TYPE)

        if mention:
            return self._resolve_mention(tracker)

        # check whether the user referred to the entity by its name
        entity_name = tracker.get_slot(entity_type)
        if entity_name:
            return entity_name

        # if no explicit mention was found, we assume the user just refers to the last
        # entity mentioned in the conversation
        return tracker.get_slot(SLOT_LAST_ENTITY)

    def _resolve_mention(self, tracker):
        """
        Resolves a mention of an entity, such as 'the first one', to the actual entity.
        If multiple entities are listed during the conversation, the entities
        are stored in the slot 'knowledge_base_entities' as a list. We resolve the
        mention, such as first, to the list index and retrieve the actual entity.
        If the mention is not an ordinal mention, but some other reference, we just
        assume the user is referring to the last mentioned entity in the conversation.

        Args:
            tracker: the tracker

        Returns: name of the actually entity
        """

        mention = tracker.get_slot(SLOT_MENTION)
        listed_items = tracker.get_slot(SLOT_LISTED_ITEMS)
        last_entity = tracker.get_slot(SLOT_LAST_ENTITY)
        last_entity_type = tracker.get_slot(SLOT_LAST_ENTITY_TYPE)
        current_entity_type = tracker.get_slot(SLOT_ENTITY_TYPE)

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

    def _to_str(self, entity_type, entity):
        """
        Converts an entity to its string representation using the lambda function
        defined in the schema

        Args:
            entity_type: the entity type
            entity: the entity with all its attributes

        Returns: a string that represents the entity
        """
        representation_func = self.knowledge_base.schema[entity_type][
            SCHEMA_KEYS_REPRESENTATION
        ]
        return representation_func(entity)

    def _get_attributes_of_entity(self, entity_type, tracker):
        """
        Checks if the NER found any value for all attributes of the given entity type.

        Args:
            entity_type: the entity type
            tracker: the tracker

        Returns: a list of attributes
        """
        attributes = []

        if entity_type not in self.knowledge_base.schema:
            return attributes

        for attr in self.knowledge_base.schema[entity_type][SCHEMA_KEYS_ATTRIBUTES]:
            attr_val = tracker.get_slot(attr)
            if attr_val is not None:
                attributes.append({"name": attr, "value": attr_val})

        return attributes

    def _reset_attribute_slots(self, entity_type, tracker):
        """
        Reset all attribute slots of the current entity type.

        Args:
            entity_type: the entity type
            tracker: the tracker

        Returns: list of reset slots
        """
        slots = []

        if entity_type not in self.knowledge_base.schema:
            return slots

        for attr in self.knowledge_base.schema[entity_type][SCHEMA_KEYS_ATTRIBUTES]:
            attr_val = tracker.get_slot(attr)
            if attr_val is not None:
                slots.append(SlotSet(attr, None))

        return slots


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

    def __init__(self, knowldege_base):
        super(ActionQueryKnowledgeBase, self).__init__(knowldege_base)

    def name(self):
        return "action_query_knowledge_base"

    def run(self, dispatcher, tracker, domain):
        entity_type = tracker.get_slot(SLOT_ENTITY_TYPE)
        last_entity_type = tracker.get_slot(SLOT_LAST_ENTITY_TYPE)
        attribute = tracker.get_slot(SLOT_ATTRIBUTE)

        new_request = entity_type != last_entity_type

        if not entity_type:
            dispatcher.utter_template(
                "Sorry, I did not get that. Can you please rephrase?", tracker
            )
            return []

        if not attribute or new_request:
            return self._query_entities(dispatcher, tracker)
        elif attribute:
            return self._query_attribute(dispatcher, tracker)

        dispatcher.utter_template(
            "Sorry, I did not get that. Can you please rephrase?", tracker
        )
        return []

    def _query_entities(self, dispatcher, tracker):
        """
        Queries the knowledge base for entities of the requested entity type and
        outputs those to the user.

        Args:
            dispatcher: the dispatcher
            tracker: the tracker

        Returns: list of slots
        """
        entity_type = tracker.get_slot(SLOT_ENTITY_TYPE)

        attributes = self._get_attributes_of_entity(entity_type, tracker)
        entities = self.knowledge_base.get_entities(entity_type, attributes)

        if not entities:
            dispatcher.utter_template(
                "I could not find any entities of type '{entity_type}'.", tracker
            )
            return []

        representation_function = self.knowledge_base.schema[entity_type][
            SCHEMA_KEYS_REPRESENTATION
        ]

        dispatcher.utter_template(
            "Found the following entities of type '{entity_type}':", tracker
        )
        for i, e in enumerate(entities, 1):
            dispatcher.utter_template(
                "{}: {}".format(i, representation_function(e)), tracker
            )

        key_attribute = self.knowledge_base.schema[entity_type][SCHEMA_KEYS_KEY]

        last_entity = None if len(entities) > 1 else entities[0][key_attribute]

        slots = [
            SlotSet(SLOT_ENTITY_TYPE, entity_type),
            SlotSet(SLOT_MENTION, None),
            SlotSet(SLOT_ATTRIBUTE, None),
            SlotSet(SLOT_LAST_ENTITY, last_entity),
            SlotSet(SLOT_LAST_ENTITY_TYPE, entity_type),
            SlotSet(SLOT_LISTED_ITEMS, list(map(lambda e: e[key_attribute], entities))),
        ]

        return slots + self._reset_attribute_slots(entity_type, tracker)

    def _query_attribute(self, dispatcher, tracker):
        """
        Queries the knowledge base for the value of the requested attribute of the
        mentioned entity and outputs it to the user.

        Args:
            dispatcher: the dispatcher
            tracker: the tracker

        Returns: list of slots
        """
        entity_type = tracker.get_slot(SLOT_ENTITY_TYPE)
        attribute = tracker.get_slot(SLOT_ATTRIBUTE)

        entity = self._get_entity(tracker)

        if not entity or not attribute:
            dispatcher.utter_template(
                "Sorry, I did not get that. Can you please rephrase?", tracker
            )

            slots = [SlotSet(SLOT_MENTION, None)]
            return slots + self._reset_attribute_slots(entity_type, tracker)

        value = self.knowledge_base.get_attribute_of(entity_type, entity, attribute)

        # utter response
        if value:
            dispatcher.utter_template(
                "'{}' has the value '{}' for attribute '{}'.".format(
                    entity, value, attribute
                ),
                tracker,
            )
        else:
            dispatcher.utter_template(
                "Did not found a valid value for attribute '{}' for entity '{}'.".format(
                    attribute, entity
                ),
                tracker,
            )

        slots = [
            SlotSet(SLOT_ENTITY_TYPE, entity_type),
            SlotSet(SLOT_MENTION, None),
            SlotSet(SLOT_LAST_ENTITY, entity),
            SlotSet(SLOT_LAST_ENTITY_TYPE, entity_type),
        ]

        return slots + self._reset_attribute_slots(entity_type, tracker)
