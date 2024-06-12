from google.protobuf import any_pb2 as _any_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Tracker(_message.Message):
    __slots__ = ["conversation_id", "slots", "latest_message", "latest_event_time", "followup_action", "paused", "events", "latest_input_channel", "active_loop", "latest_action"]
    class SlotsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class LatestMessageEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class ActiveLoopEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class LatestActionEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    CONVERSATION_ID_FIELD_NUMBER: _ClassVar[int]
    SLOTS_FIELD_NUMBER: _ClassVar[int]
    LATEST_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    LATEST_EVENT_TIME_FIELD_NUMBER: _ClassVar[int]
    FOLLOWUP_ACTION_FIELD_NUMBER: _ClassVar[int]
    PAUSED_FIELD_NUMBER: _ClassVar[int]
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    LATEST_INPUT_CHANNEL_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_LOOP_FIELD_NUMBER: _ClassVar[int]
    LATEST_ACTION_FIELD_NUMBER: _ClassVar[int]
    conversation_id: str
    slots: _containers.ScalarMap[str, str]
    latest_message: _containers.ScalarMap[str, str]
    latest_event_time: float
    followup_action: str
    paused: bool
    events: _containers.RepeatedScalarFieldContainer[str]
    latest_input_channel: str
    active_loop: _containers.ScalarMap[str, str]
    latest_action: _containers.ScalarMap[str, str]
    def __init__(self, conversation_id: _Optional[str] = ..., slots: _Optional[_Mapping[str, str]] = ..., latest_message: _Optional[_Mapping[str, str]] = ..., latest_event_time: _Optional[float] = ..., followup_action: _Optional[str] = ..., paused: bool = ..., events: _Optional[_Iterable[str]] = ..., latest_input_channel: _Optional[str] = ..., active_loop: _Optional[_Mapping[str, str]] = ..., latest_action: _Optional[_Mapping[str, str]] = ...) -> None: ...

class Domain(_message.Message):
    __slots__ = ["config", "session_config", "intents", "entities", "slots", "responses", "actions", "forms", "e2e_actions"]
    class ConfigEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class SessionConfigEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class SlotsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class ResponsesEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class FormsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    SESSION_CONFIG_FIELD_NUMBER: _ClassVar[int]
    INTENTS_FIELD_NUMBER: _ClassVar[int]
    ENTITIES_FIELD_NUMBER: _ClassVar[int]
    SLOTS_FIELD_NUMBER: _ClassVar[int]
    RESPONSES_FIELD_NUMBER: _ClassVar[int]
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    FORMS_FIELD_NUMBER: _ClassVar[int]
    E2E_ACTIONS_FIELD_NUMBER: _ClassVar[int]
    config: _containers.ScalarMap[str, str]
    session_config: _containers.ScalarMap[str, str]
    intents: _containers.RepeatedScalarFieldContainer[str]
    entities: _containers.RepeatedScalarFieldContainer[str]
    slots: _containers.ScalarMap[str, str]
    responses: _containers.ScalarMap[str, str]
    actions: _containers.RepeatedScalarFieldContainer[str]
    forms: _containers.ScalarMap[str, str]
    e2e_actions: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, config: _Optional[_Mapping[str, str]] = ..., session_config: _Optional[_Mapping[str, str]] = ..., intents: _Optional[_Iterable[str]] = ..., entities: _Optional[_Iterable[str]] = ..., slots: _Optional[_Mapping[str, str]] = ..., responses: _Optional[_Mapping[str, str]] = ..., actions: _Optional[_Iterable[str]] = ..., forms: _Optional[_Mapping[str, str]] = ..., e2e_actions: _Optional[_Iterable[str]] = ...) -> None: ...

class WebhookRequest(_message.Message):
    __slots__ = ["next_action", "sender_id", "tracker", "domain", "version"]
    NEXT_ACTION_FIELD_NUMBER: _ClassVar[int]
    SENDER_ID_FIELD_NUMBER: _ClassVar[int]
    TRACKER_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    next_action: str
    sender_id: str
    tracker: Tracker
    domain: Domain
    version: str
    def __init__(self, next_action: _Optional[str] = ..., sender_id: _Optional[str] = ..., tracker: _Optional[_Union[Tracker, _Mapping]] = ..., domain: _Optional[_Union[Domain, _Mapping]] = ..., version: _Optional[str] = ...) -> None: ...

class WebhookResponse(_message.Message):
    __slots__ = ["events", "responses"]
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    RESPONSES_FIELD_NUMBER: _ClassVar[int]
    events: _containers.RepeatedCompositeFieldContainer[_any_pb2.Any]
    responses: _containers.RepeatedCompositeFieldContainer[_any_pb2.Any]
    def __init__(self, events: _Optional[_Iterable[_Union[_any_pb2.Any, _Mapping]]] = ..., responses: _Optional[_Iterable[_Union[_any_pb2.Any, _Mapping]]] = ...) -> None: ...
