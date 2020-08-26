from typing import Any, Dict, List, Optional, Text, Union

from typing_extensions import TypedDict


class TrackerState(TypedDict):
    sender_id: Text
    slots: Dict[Text, Any]
    latest_message: Optional[Dict[Text, Any]]
    events: List[Dict[Text, Any]]
    paused: bool
    followup_action: Optional[Text]
    active_loop: Dict[Text, Any]
    # `active_form` is deprecated
    active_form: Dict[Text, Any]
    latest_action_name: Optional[Text]


class DomainDict(TypedDict):
    intents: List[Union[Text, Dict[Text, Any]]]
    entities: List[Text]
    slots: Dict[Any, Dict[Text, Any]]
    responses: Dict[Text, List[Dict[Text, Any]]]
    actions: List[Text]
    forms: List[Union[Text, Dict]]


class ActionCall(TypedDict):
    next_action: Optional[Text]
    sender_id: Text
    tracker: TrackerState
    domain: DomainDict
    version: Text
