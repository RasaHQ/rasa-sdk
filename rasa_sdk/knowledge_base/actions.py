# -*- coding: utf-8 -*-
from rasa_sdk import Action
from rasa_sdk.events import SlotSet
from rasa_sdk.knowledge_base.utils import (
    SLOT_OBJECT_TYPE,
    SLOT_LAST_OBJECT_TYPE,
    SLOT_ATTRIBUTE,
    reset_attribute_slots,
    SLOT_MENTION,
    SLOT_LAST_OBJECT,
    SLOT_LISTED_OBJECTS,
    get_object_name,
    get_attribute_slots,
)


class ActionQueryKnowledgeBase(Action):
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

    def __init__(self, knowledge_base, use_last_object_mention=True):
        # type: (KnowledgeBase, bool)
        self.knowledge_base = knowledge_base
        self.use_last_object_mention = use_last_object_mention

    def name(self):
        # type: () -> Text
        return "action_query_knowledge_base"

    def utter_attribute_value(
        self, dispatcher, object_name, attribute_name, attribute_value
    ):
        # type: (CollectingDispatcher, Text, Text, Text) -> None
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
                "Did not find a valid value for attribute '{}' for object '{}'.".format(
                    attribute_name, object_name
                )
            )

    def utter_objects(self, dispatcher, object_type, objects):
        # type: (CollectingDispatcher, Text, List[Dict[Text, Any]]) -> None
        """
        Utters a response to the user that lists all found objects.

        Args:
            dispatcher: the dispatcher
            object_type: the object type
            objects: the list of objects
        """
        if objects:
            dispatcher.utter_message(
                "Found the following objects of type '{}':".format(object_type)
            )

            repr_function = self.knowledge_base.get_representation_function_of_object(
                object_type
            )
            for i, obj in enumerate(objects, 1):
                dispatcher.utter_message("{}: {}".format(i, repr_function(obj)))
        else:
            dispatcher.utter_message(
                "I could not find any objects of type '{}'.".format(object_type)
            )

    def run(self, dispatcher, tracker, domain):
        # type: (CollectingDispatcher, Tracker, Dict[Text, Any]) -> List[Dict]
        """
        Executes this action. If the user ask a question about an attribute,
        the knowledge base is queried for that attribute. Otherwise, if no
        attribute was detected in the request or the user is talking about a new
        object type, multiple objects of the requested type are returned from the
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
            # object type always needs to be set as this is needed to query the
            # knowledge base
            dispatcher.utter_template("utter_ask_rephrase", tracker)
            return []

        if not attribute or new_request:
            return self._query_objects(dispatcher, tracker)
        elif attribute:
            return self._query_attribute(dispatcher, tracker)

        dispatcher.utter_template("utter_ask_rephrase", tracker)
        return []

    def _query_objects(self, dispatcher, tracker):
        # type: (CollectingDispatcher, Tracker) -> List[Dict]
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
        object_attributes = self.knowledge_base.get_attributes_of_object(object_type)

        # get all set attribute slots of the object type to be able to filter the
        # list of objects
        attributes = get_attribute_slots(tracker, object_attributes)
        # query the knowledge base
        objects = self.knowledge_base.get_objects(object_type, attributes)

        self.utter_objects(dispatcher, object_type, objects)

        if not objects:
            return reset_attribute_slots(tracker, object_attributes)

        key_attribute = self.knowledge_base.get_key_attribute_of_object(object_type)

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

        return slots + reset_attribute_slots(tracker, object_attributes)

    def _query_attribute(self, dispatcher, tracker):
        # type: (CollectingDispatcher, Tracker) -> List[Dict]
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

        object_name = get_object_name(
            tracker,
            self.knowledge_base.ordinal_mention_mapping,
            self.use_last_object_mention,
        )

        if not object_name or not attribute:
            dispatcher.utter_template("utter_ask_rephrase", tracker)
            return [SlotSet(SLOT_MENTION, None)]

        object_of_interest = self.knowledge_base.get_object(object_type, object_name)

        if not object_of_interest or attribute not in object_of_interest:
            dispatcher.utter_template("utter_ask_rephrase", tracker)
            return [SlotSet(SLOT_MENTION, None)]

        value = object_of_interest[attribute]
        repr_function = self.knowledge_base.get_representation_function_of_object(
            object_type
        )
        object_representation = repr_function(object_of_interest)
        key_attribute = self.knowledge_base.get_key_attribute_of_object(object_type)
        object_identifier = object_of_interest[key_attribute]

        self.utter_attribute_value(dispatcher, object_representation, attribute, value)

        slots = [
            SlotSet(SLOT_OBJECT_TYPE, object_type),
            SlotSet(SLOT_ATTRIBUTE, None),
            SlotSet(SLOT_MENTION, None),
            SlotSet(SLOT_LAST_OBJECT, object_identifier),
            SlotSet(SLOT_LAST_OBJECT_TYPE, object_type),
        ]

        return slots
