from typing import Any, Dict, Text
from rasa_sdk.executor import ActionExecutor, CollectingDispatcher
from rasa_sdk.forms import ValidationAction
from rasa_sdk.types import ActionCall, DomainDict
from rasa_sdk import Tracker


# This file contains all attribute extractors for tracing instrumentation.
# These are functions that are applied to the arguments of the wrapped function to be
# traced to extract the attributes that we want to forward to our tracing backend.
# Note that we always mirror the argument lists of the wrapped functions, as our
# wrapping mechanism always passes in the original arguments unchanged for further
# processing.


def extract_attrs_for_action_executor(
    self: ActionExecutor,
    action_call: ActionCall,
) -> Dict[Text, Any]:
    """Extract the attributes for `ActionExecutor.run`.

    :param self: The `ActionExecutor` on which `run` is called.
    :param action_call: The `ActionCall` argument.
    :return: A dictionary containing the attributes.
    """
    attributes = {"sender_id": action_call["sender_id"]}
    action_name = action_call.get("next_action")

    if action_name:
        attributes["action_name"] = action_name

    return attributes


def extract_attrs_for_validation_action(
    self: ValidationAction,
    dispatcher: "CollectingDispatcher",
    tracker: "Tracker",
    domain: "DomainDict",
) -> Dict[Text, Any]:
    """Extract the attributes for `ValidationAction.run`.

    :param self: The `ValidationAction` on which `run` is called.
    :param dispatcher: The `CollectingDispatcher` argument.
    :param tracker: The `Tracker` argument.
    :param domain: The `DomainDict` argument.
    :return: A dictionary containing the attributes.
    """
    slots_to_validate = tracker.slots_to_validate().keys()

    return {
        "class_name": self.__class__.__name__,
        "sender_id": tracker.sender_id,
        "slots_to_validate": str(slots_to_validate),
        "action_name": self.name(),
    }
