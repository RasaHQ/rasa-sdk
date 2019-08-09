# -*- coding: utf-8 -*-
from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from rasa_sdk.knowledge_base.storage import (
    SCHEMA_KEYS_ATTRIBUTES,
    SCHEMA_KEYS_REPRESENTATION,
    SCHEMA_KEYS_KEY,
)


SLOT_MENTION = "mention"
SLOT_OBJECT_TYPE = "object_type"
SLOT_ATTRIBUTE = "attribute"
SLOT_LISTED_OBJECTS = "knowledge_base_listed_objects"
SLOT_LAST_OBJECT = "knowledge_base_last_object"
SLOT_LAST_OBJECT_TYPE = "knowledge_base_last_object_type"


class ActionKnowledgeBase(Action):
    """
    Abstract knowledge base action that can be inherited to create custom actions
    that are able to interact with a knowledge base.
    """

    def __init__(self, knowledge_base):
        self.knowledge_base = knowledge_base

    def _get_object_name(self, tracker):
        """
        Get the name of the object the user referred to. Either the NER detected the
        object and stored its name in the corresponding slot (e.g. "Pasta&Pizza Place"
        is detected as "restaurant") or the user referred to the object by any kind of
        mention, such as "first one" or "it".

        Args:
            tracker: the tracker

        Returns: the name of the actual object (value of key attribute in the
        knowledge base)
        """
        mention = tracker.get_slot(SLOT_MENTION)
        object_type = tracker.get_slot(SLOT_OBJECT_TYPE)

        # the user referred to the object by a mention, such as "first one"
        if mention:
            return self._resolve_mention(tracker)

        # check whether the user referred to the objet by its name
        object_name = tracker.get_slot(object_type)
        if object_name:
            return object_name

        # if no explicit mention was found, we assume the user just refers to the last
        # object mentioned in the conversation
        return tracker.get_slot(SLOT_LAST_OBJECT)

    def _resolve_mention(self, tracker):
        """
        Resolve the given mention to the name of the actual object.

        Different kind of mentions exist. We distinguish between ordinal mentions and
        all others for now.
        For ordinal mentions we resolve the mention of an object, such as 'the first
        one', to the actual object name. If multiple objects are listed during the
        conversation, the objects are stored in the slot 'knowledge_base_listed_objects'
        as a list. We resolve the mention, such as 'the first one', to the list index
        and retrieve the actual object.
        For any other mention, such as 'it' or 'that restaurant', we just assume the
        user is referring to the last mentioned object in the conversation.

        Args:
            tracker: the tracker

        Returns: name of the actually object
        """

        mention = tracker.get_slot(SLOT_MENTION)
        listed_items = tracker.get_slot(SLOT_LISTED_OBJECTS)
        last_object = tracker.get_slot(SLOT_LAST_OBJECT)
        last_object_type = tracker.get_slot(SLOT_LAST_OBJECT_TYPE)
        current_object_type = tracker.get_slot(SLOT_OBJECT_TYPE)

        if not mention:
            return None

        if listed_items and mention in self.knowledge_base.ordinal_mention_mapping:
            idx_function = self.knowledge_base.ordinal_mention_mapping[mention]
            return idx_function(listed_items)

        # NOTE:
        # for now we just assume that if the user refers to an object, for
        # example via "it" or "that restaurant", they are actually referring to the last
        # object that was detected.
        if current_object_type == last_object_type:
            return last_object

    def _to_str(self, object_type, object_dict):
        """
        Converts an object to its string representation using the lambda function
        defined in the schema.

        Args:
            object_type: the object type
            object_dict: the object with all its attributes

        Returns: a string that represents the object
        """
        representation_func = self.knowledge_base.schema[object_type][
            SCHEMA_KEYS_REPRESENTATION
        ]
        return representation_func(object_dict)

    def _get_attributes_of_object(self, tracker, object_type):
        """
        If the user mentioned one or multiple attributes of the provided object_type in
        an utterance, we extract all attribute values from the tracker and put them
        in a list. The list is used later on to filter a list of objects.

        For example: The user says 'What Italian restaurants do you know?'.
        The NER should detect 'Italian' as 'cuisine'.
        Due to the schema definition we know that 'cuisine' is an attribute of the
        object type 'restaurant'.
        Thus, this method returns [{'name': 'cuisine', 'value': 'Italian'}] as
        list of attributes for the object type 'restaurant'.

        Args:
            tracker: the tracker
            object_type: the object type

        Returns: a list of attributes
        """
        attributes = []

        if object_type not in self.knowledge_base.schema:
            return attributes

        for attr in self.knowledge_base.schema[object_type][SCHEMA_KEYS_ATTRIBUTES]:
            attr_val = tracker.get_slot(attr)
            if attr_val is not None:
                attributes.append({"name": attr, "value": attr_val})

        return attributes

    def _reset_attribute_slots(self, tracker, object_type):
        """
        Reset all attribute slots of the current object type.

        If the user is saying something like "Show me all restaurants with Italian
        cuisine.", the NER should detect "restaurant" as "object_type" and "Italian" as
        "cuisine" object. So, we should filter the restaurant objects in the
        knowledge base by their cuisine (= Italian). When listing objects, we check
        what attributes are detected by the NER. We take all attributes that are set,
        e.g. cuisine = Italian. If we don't reset the attribute slots after the request
        is done and the next utterance of the user would be, for example, "List all
        restaurants that have wifi.", we would have two attribute slots set: "wifi" and
        "cuisine". Thus, we would filter all restaurants for two attributes now:
        wifi = True and cuisine = Italian. However, the user did not specify any
        cuisine in the request. To avoid that we reset the attribute slots once the
        request is done.

        Args:
            object_type: the object type
            tracker: the tracker

        Returns: list of slots
        """
        slots = []

        if object_type not in self.knowledge_base.schema:
            return slots

        for attr in self.knowledge_base.schema[object_type][SCHEMA_KEYS_ATTRIBUTES]:
            attr_val = tracker.get_slot(attr)
            if attr_val is not None:
                slots.append(SlotSet(attr, None))

        return slots


class ActionQueryKnowledgeBase(ActionKnowledgeBase):
    """
    Action that queries the knowledge base for objects and attributes of an object.
    The action needs to be inherited and the knowledge base needs to be set.
    In order to actually query the knowledge base you need to:
    - create your knowledge base
    - add mandatory slots to the domain file: 'object_type', 'attribute', 'mention'
    - create NLU data where the required objects are annotated
    - create a story that includes this action
    - add the intent and action to domain file
    """

    def __init__(self, knowldege_base):
        super(ActionQueryKnowledgeBase, self).__init__(knowldege_base)

    def name(self):
        return "action_query_knowledge_base"

    def utter_rephrase(self, dispatcher):
        """
        Utters a response to the user that indicates that something went wrong. It
        asks the user to rephrase his request.

        Args:
            dispatcher: the dispatcher
        """
        dispatcher.utter_message("Sorry, I did not get that. Can you please rephrase?")

    def utter_attribute_value(
        self, dispatcher, object_name, attribute_name, attribute_value
    ):
        """
        Utters a response that informs the user about the attribute value of the
        attribute of interest.

        Args:
            dispatcher: the dispatcher
            object_name: the name of the object
            attribute_name: the name of the attribute
            attribute_value: the value of the attribute
        """
        if attribute_value:
            dispatcher.utter_message(
                "'{}' has the value '{}' for attribute '{}'.".format(
                    object_name, attribute_value, attribute_name
                )
            )
        else:
            dispatcher.utter_message(
                "Did not found a valid value for attribute '{}' for object '{}'.".format(
                    attribute_name, object_name
                )
            )

    def utter_objects(self, dispatcher, object_type, objects):
        """
        Utters a response to the user that lists all found objects.

        Args:
            dispatcher: the dispatcher
            object_type: the object type
            objects: the list of objects
        """
        dispatcher.utter_message(
            "Found the following objects of type '{}':".format(object_type)
        )
        for i, obj in enumerate(objects, 1):
            dispatcher.utter_message("{}: {}".format(i, self._to_str(object_type, obj)))

    def utter_no_objects_found(self, dispatcher, object_type):
        """
        Utters a response that informs the user that no object could be found.

        Args:
            dispatcher: the dispatcher
            object_type: the object type
        """
        dispatcher.utter_message(
            "I could not find any objects of type '{}'.".format(object_type)
        )

    def run(self, dispatcher, tracker, domain):
        """
        Executes this action. If the user ask an question about an attribute,
        the knowledge base is queried for that attribute. Otherwise, if no
        attribute was detected in the request or the user is talking about a new
        object, multiple objects of the requested type are returned from the
        knowledge base.

        Args:
            dispatcher: the dispatcher
            tracker: the tracker
            domain: the domain

        Returns: list of slots

        """
        object_type = tracker.get_slot(SLOT_OBJECT_TYPE)
        last_object_type = tracker.get_slot(SLOT_LAST_OBJECT_TYPE)
        attribute = tracker.get_slot(SLOT_ATTRIBUTE)

        new_request = object_type != last_object_type

        if not object_type:
            self.utter_rephrase(dispatcher)
            return []

        if not attribute or new_request:
            return self._query_objects(dispatcher, tracker)
        elif attribute:
            return self._query_attribute(dispatcher, tracker)

        self.utter_rephrase(dispatcher)
        return []

    def _query_objects(self, dispatcher, tracker):
        """
        Queries the knowledge base for objects of the requested object type and
        outputs those to the user. The objects are filtered by any attribute the
        user mentioned in the request.

        Args:
            dispatcher: the dispatcher
            tracker: the tracker

        Returns: list of slots
        """
        object_type = tracker.get_slot(SLOT_OBJECT_TYPE)

        # get all set attribute slots of the object type to be able to filter the
        # list of objects
        attributes = self._get_attributes_of_object(tracker, object_type)
        # query the knowledge base
        objects = self.knowledge_base.get_objects(object_type, attributes)

        if not objects:
            self.utter_no_objects_found(dispatcher, tracker)
            return self._reset_attribute_slots(tracker, object_type)

        self.utter_objects(dispatcher, object_type, objects)

        key_attribute = self.knowledge_base.schema[object_type][SCHEMA_KEYS_KEY]

        last_object = None if len(objects) > 1 else objects[0][key_attribute]

        slots = [
            SlotSet(SLOT_OBJECT_TYPE, object_type),
            SlotSet(SLOT_MENTION, None),
            SlotSet(SLOT_ATTRIBUTE, None),
            SlotSet(SLOT_LAST_OBJECT, last_object),
            SlotSet(SLOT_LAST_OBJECT_TYPE, object_type),
            SlotSet(
                SLOT_LISTED_OBJECTS, list(map(lambda e: e[key_attribute], objects))
            ),
        ]

        return slots + self._reset_attribute_slots(tracker, object_type)

    def _query_attribute(self, dispatcher, tracker):
        """
        Queries the knowledge base for the value of the requested attribute of the
        mentioned object and outputs it to the user.

        Args:
            dispatcher: the dispatcher
            tracker: the tracker

        Returns: list of slots
        """
        object_type = tracker.get_slot(SLOT_OBJECT_TYPE)
        attribute = tracker.get_slot(SLOT_ATTRIBUTE)

        object_name = self._get_object_name(tracker)

        if not object_name or not attribute:
            self.utter_rephrase(dispatcher)
            slots = [SlotSet(SLOT_MENTION, None)]
            return slots

        value = self.knowledge_base.get_attribute_of(
            object_type, object_name, attribute
        )

        self.utter_attribute_value(dispatcher, object_name, attribute, value)

        slots = [
            SlotSet(SLOT_OBJECT_TYPE, object_type),
            SlotSet(SLOT_MENTION, None),
            SlotSet(SLOT_LAST_OBJECT, object_name),
            SlotSet(SLOT_LAST_OBJECT_TYPE, object_type),
        ]

        return slots
