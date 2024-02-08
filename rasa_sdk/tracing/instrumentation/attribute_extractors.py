from typing import Any, Dict, Text
from rasa_sdk.executor import ActionExecutor
from rasa_sdk.types import ActionCall


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
