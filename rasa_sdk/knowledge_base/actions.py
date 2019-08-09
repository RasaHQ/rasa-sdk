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
    that are able to interact with a knowledge base.
    """

    def __init__(self, knowledge_base):
        self.knowledge_base = knowledge_base

    def _get_entity(self, tracker):
        """
        Get the name of the entity the user referred to. Either the NER detected the
        entity and stored its name in the corresponding slot (e.g. "Pasta&Pizza Place"
        is detected as "restaurant") or the user referred to the entity by any kind of
        mention, such as "first one" or "it".

        Args:
            tracker: the tracker

        Returns: the name of the actual entity (value of key attribute in the
        knowledge base)
        """
        mention = tracker.get_slot(SLOT_MENTION)
        entity_type = tracker.get_slot(SLOT_ENTITY_TYPE)

        # the user referred to the entity by a mention, such as "first one"
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
        Resolve the given mention to the name of the actual entity.

        Different kind of mentions exist. We distinguish between ordinal mentions and
        all others.
        For ordinal mentions we resolve the mention of an entity, such as 'the first
        one', to the actual entity. If multiple entities are listed during the
        conversation, the entities are stored in the slot 'knowledge_base_listed_items'
        as a list. We resolve the mention, such as 'the first one', to the list index
        and retrieve the actual entity.
        For any other mention, such as 'it' or 'that restaurant', we just assume the
        user is referring to the last mentioned entity in the conversation.

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
        # for now we just assume that if the user refers to an entity, for
        # example via "it" or "that restaurant", they are actually referring to the last
        # entity that was detected.
        if current_entity_type == last_entity_type:
            return last_entity

    def _to_str(self, entity_type, entity):
        """
        Converts an entity to its string representation using the lambda function
        defined in the schema.

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
        If the user mentioned one or multiple attributes of the provided entity_type in
        his utterance, we extract all attribute values from the tracker and put them
        in a list. The list is used later on to filter a list of entities.

        For example: The user says 'What Italian restaurants do you know?'.
        The NER should detect 'Italian' as 'cuisine'.
        Due to the schema definition we know that 'cuisine' is an attribute of the
        entity type 'restaurant'.
        Thus, this method returns [{'name': 'cuisine', 'value': 'Italian'}] as
        list of attributes for the entity type 'restaurant'.

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

        If the user is saying something like "Show me all restaurants with Italian
        cuisine.", the NER should detect "restaurant" as "entity_type" and "Italian" as
        "cuisine" entity. So, we should filter the restaurant entities in the
        knowledge base by their cuisine (= Italian). When listing entities, we check
        what attributes are detected by the NER. We take all attributes that are set,
        e.g. cuisine = Italian. If we don't reset the attribute slots after the request
        is done and the next utterance of the user would be, for example, "List all
        restaurants that have wifi.", we would have two attribute slots set: "wifi" and
        "cuisine". Thus, we would filter all restaurants for two attributes now:
        wifi = True and cuisine = Italian. However, the user did not specify any
        cuisine in his request. To avoid that we reset the attribute slots once the
        request is done.

        Args:
            entity_type: the entity type
            tracker: the tracker

        Returns: list of slots
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
    - create NLU data where the required entities are annotated
    - create a story that includes this action
    - add the intent and action to domain file
    """

    def __init__(self, knowldege_base):
        super(ActionQueryKnowledgeBase, self).__init__(knowldege_base)

    def name(self):
        return "action_query_knowledge_base"

    def utter_rephrase(self, dispatcher, tracker):
        """
        Utters a response to the user that indicates that something went wrong. It
        asks the user to rephrase his request.

        Args:
            dispatcher: the dispatcher
            tracker: the tracker
        """
        dispatcher.utter_template(
            "Sorry, I did not get that. Can you please rephrase?", tracker
        )

    def utter_attribute_value(self, dispatcher, tracker, entity, attribute, value):
        """
        Utters a response that informs the user about the attribute value of the
        attribute of interest.

        Args:
            dispatcher: the dispatcher
            tracker: the tracker
        """
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

    def utter_entities(self, dispatcher, tracker, representation_function, entities):
        """
        Utters a response to the user that lists all found entities.

        Args:
            dispatcher: the dispatcher
            tracker: the tracker
        """
        dispatcher.utter_template(
            "Found the following entities of type '{entity_type}':", tracker
        )
        for i, e in enumerate(entities, 1):
            dispatcher.utter_template(
                "{}: {}".format(i, representation_function(e)), tracker
            )

    def utter_no_entities_found(self, dispatcher, tracker):
        """
        Utters a response that informs the user that no entity could be found.

        Args:
            dispatcher: the dispatcher
            tracker: the tracker
        """
        dispatcher.utter_template(
            "I could not find any entities of type '{entity_type}'.", tracker
        )

    def run(self, dispatcher, tracker, domain):
        """
        Executes this action. If the user ask an question about an attribute,
        the knowledge base is queried for that attribute. Otherwise, if no
        attribute was detected in the request or the user is talking about a new
        entity, multiple entities of the requested type are returned from the
        knowledge base.

        Args:
            dispatcher: the dispatcher
            tracker: the tracker
            domain: the domain

        Returns: list of slots

        """
        entity_type = tracker.get_slot(SLOT_ENTITY_TYPE)
        last_entity_type = tracker.get_slot(SLOT_LAST_ENTITY_TYPE)
        attribute = tracker.get_slot(SLOT_ATTRIBUTE)

        new_request = entity_type != last_entity_type

        if not entity_type:
            self.utter_rephrase(dispatcher, tracker)
            return []

        if not attribute or new_request:
            return self._query_entities(dispatcher, tracker)
        elif attribute:
            return self._query_attribute(dispatcher, tracker)

        self.utter_rephrase(dispatcher, tracker)
        return []

    def _query_entities(self, dispatcher, tracker):
        """
        Queries the knowledge base for entities of the requested entity type and
        outputs those to the user. The entities are filtered by any attribute the
        user mentioned in the request.

        Args:
            dispatcher: the dispatcher
            tracker: the tracker

        Returns: list of slots
        """
        entity_type = tracker.get_slot(SLOT_ENTITY_TYPE)

        # get all set attribute slots of the entity type to be able to filter the
        # list of entities
        attributes = self._get_attributes_of_entity(entity_type, tracker)
        # query the knowledge base
        entities = self.knowledge_base.get_entities(entity_type, attributes)

        if not entities:
            self.utter_no_entities_found(dispatcher, tracker)
            return self._reset_attribute_slots(entity_type, tracker)

        representation_function = self.knowledge_base.schema[entity_type][
            SCHEMA_KEYS_REPRESENTATION
        ]

        self.utter_entities(dispatcher, tracker, representation_function, entities)

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
            self.utter_rephrase(dispatcher, tracker)
            slots = [SlotSet(SLOT_MENTION, None)]
            return slots

        value = self.knowledge_base.get_attribute_of(entity_type, entity, attribute)

        self.utter_attribute_value(attribute, dispatcher, entity, tracker, value)

        slots = [
            SlotSet(SLOT_ENTITY_TYPE, entity_type),
            SlotSet(SLOT_MENTION, None),
            SlotSet(SLOT_LAST_ENTITY, entity),
            SlotSet(SLOT_LAST_ENTITY_TYPE, entity_type),
        ]

        return slots
