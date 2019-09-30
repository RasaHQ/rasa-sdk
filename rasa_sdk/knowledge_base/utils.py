from rasa_sdk.events import SlotSet
from typing import Text, Callable, Dict, List, Any, Optional
import typing

SLOT_MENTION = "mention"
SLOT_OBJECT_TYPE = "object_type"
SLOT_ATTRIBUTE = "attribute"
SLOT_LISTED_OBJECTS = "knowledge_base_listed_objects"
SLOT_LAST_OBJECT = "knowledge_base_last_object"
SLOT_LAST_OBJECT_TYPE = "knowledge_base_last_object_type"

if typing.TYPE_CHECKING:
    from rasa_sdk.executor import Tracker


def get_object_name(
    tracker: "Tracker",
    ordinal_mention_mapping: Dict[Text, Callable],
    use_last_object_mention: bool = True,
) -> Optional[Text]:
    """
    Get the name of the object the user referred to. Either the NER detected the
    object and stored its name in the corresponding slot (e.g. "PastaBar"
    is detected as "restaurant") or the user referred to the object by any kind of
    mention, such as "first one" or "it".

    Args:
        tracker: the tracker
        ordinal_mention_mapping: mapping that maps an ordinal mention to an object in a list
        use_last_object_mention: if true the last mentioned object is returned if
        no other mention could be detected

    Returns: the name of the actual object (value of key attribute in the
    knowledge base)
    """
    mention = tracker.get_slot(SLOT_MENTION)
    object_type = tracker.get_slot(SLOT_OBJECT_TYPE)

    # the user referred to the object by a mention, such as "first one"
    if mention:
        return resolve_mention(tracker, ordinal_mention_mapping)

    # check whether the user referred to the objet by its name
    object_name = tracker.get_slot(object_type)
    if object_name:
        return object_name

    if use_last_object_mention:
        # if no explicit mention was found, we assume the user just refers to the last
        # object mentioned in the conversation
        return tracker.get_slot(SLOT_LAST_OBJECT)

    return None


def resolve_mention(
    tracker: "Tracker", ordinal_mention_mapping: Dict[Text, Callable]
) -> Optional[Text]:
    """
    Resolve the given mention to the name of the actual object.

    Different kind of mentions exist. We distinguish between ordinal mentions and
    all others for now.
    For ordinal mentions we resolve the mention of an object, such as 'the first
    one', to the actual object name. If multiple objects are listed during the
    conversation, the objects are stored in the slot 'knowledge_base_listed_objects'
    as a list. We resolve the mention, such as 'the first one', to the list index
    and retrieve the actual object (using the 'ordinal_mention_mapping').
    For any other mention, such as 'it' or 'that restaurant', we just assume the
    user is referring to the last mentioned object in the conversation.

    Args:
        tracker: the tracker
        ordinal_mention_mapping: mapping that maps an ordinal mention to an object in a list

    Returns: name of the actually object
    """

    mention = tracker.get_slot(SLOT_MENTION)
    listed_items = tracker.get_slot(SLOT_LISTED_OBJECTS)
    last_object = tracker.get_slot(SLOT_LAST_OBJECT)
    last_object_type = tracker.get_slot(SLOT_LAST_OBJECT_TYPE)
    current_object_type = tracker.get_slot(SLOT_OBJECT_TYPE)

    if not mention:
        return None

    if listed_items and mention in ordinal_mention_mapping:
        idx_function = ordinal_mention_mapping[mention]
        return idx_function(listed_items)

    # NOTE:
    # for now we just assume that if the user refers to an object, for
    # example via "it" or "that restaurant", they are actually referring to the last
    # object that was detected.
    if current_object_type == last_object_type:
        return last_object


def get_attribute_slots(
    tracker: "Tracker", object_attributes: List[Text]
) -> List[Dict[Text, Text]]:
    """
    If the user mentioned one or multiple attributes of the provided object_type in
    an utterance, we extract all attribute values from the tracker and put them
    in a list. The list is used later on to filter a list of objects.

    For example: The user says 'What Italian restaurants do you know?'.
    The NER should detect 'Italian' as 'cuisine'.
    We know that 'cuisine' is an attribute of the object type 'restaurant'.
    Thus, this method returns [{'name': 'cuisine', 'value': 'Italian'}] as
    list of attributes for the object type 'restaurant'.

    Args:
        tracker: the tracker
        object_attributes: list of potential attributes of object

    Returns: a list of attributes
    """
    attributes = []

    for attr in object_attributes:
        attr_val = tracker.get_slot(attr) if attr in tracker.slots else None
        if attr_val is not None:
            attributes.append({"name": attr, "value": attr_val})

    return attributes


def reset_attribute_slots(
    tracker: "Tracker", object_attributes: List[Text]
) -> List[Dict]:
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
        tracker: the tracker
        object_attributes: list of potential attributes of object

    Returns: list of slots
    """
    slots = []

    for attr in object_attributes:
        attr_val = tracker.get_slot(attr) if attr in tracker.slots else None
        if attr_val is not None:
            slots.append(SlotSet(attr, None))

    return slots
