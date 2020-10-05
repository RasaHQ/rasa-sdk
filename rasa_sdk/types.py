from typing import Any, Dict, List, Optional, Text

from typing_extensions import TypedDict


class TrackerState(TypedDict):
    """
    A dictionary representation of the state of a conversation.
    """

    # id of the source of the messages
    sender_id: Text
    # the currently set values of the slots
    slots: Dict[Text, Any]
    # the most recent message sent by the user
    latest_message: Optional[Dict[Text, Any]]
    # list of previously seen events
    events: List[Dict[Text, Any]]
    # whether the tracker is currently paused
    paused: bool
    # a deterministically scheduled action to be executed next
    followup_action: Optional[Text]
    # the loop that is currently active
    active_loop: Dict[Text, Any]
    # `active_form` is deprecated in favor of `active_loop`
    active_form: Dict[Text, Any]
    # the name of the previously executed action or text of e2e action
    latest_action_name: Optional[Text]


class DomainDict(TypedDict):
    """
    A dictionary representation of the domain.
    """

    intents: List[Dict[Text, Any]]
    entities: List[Text]
    slots: Dict[Any, Dict[Text, Any]]
    responses: Dict[Text, List[Dict[Text, Any]]]
    actions: List[Text]
    forms: Dict[Text, Any]


class ActionCall(TypedDict):
    """
    A dictionary representation of an action to be executed.
    """

    # the name of the next action to be executed
    next_action: Optional[Text]
    # id of the source of the messages
    sender_id: Text
    # current dictionary representation of the state of a conversation
    tracker: TrackerState
    # dictionary representation of the domain
    domain: DomainDict
    # rasa version
    version: Text
