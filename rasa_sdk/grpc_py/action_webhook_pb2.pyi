from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ActionsRequest(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class ActionsResponse(_message.Message):
    __slots__ = ["actions"]
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    actions: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    def __init__(self, actions: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ...) -> None: ...

class Tracker(_message.Message):
    __slots__ = ["sender_id", "slots", "latest_message", "events", "paused", "followup_action", "active_loop", "latest_action_name", "stack"]
    class ActiveLoopEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SENDER_ID_FIELD_NUMBER: _ClassVar[int]
    SLOTS_FIELD_NUMBER: _ClassVar[int]
    LATEST_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    PAUSED_FIELD_NUMBER: _ClassVar[int]
    FOLLOWUP_ACTION_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_LOOP_FIELD_NUMBER: _ClassVar[int]
    LATEST_ACTION_NAME_FIELD_NUMBER: _ClassVar[int]
    STACK_FIELD_NUMBER: _ClassVar[int]
    sender_id: str
    slots: _struct_pb2.Struct
    latest_message: _struct_pb2.Struct
    events: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    paused: bool
    followup_action: str
    active_loop: _containers.ScalarMap[str, str]
    latest_action_name: str
    stack: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    def __init__(self, sender_id: _Optional[str] = ..., slots: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., latest_message: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., events: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ..., paused: bool = ..., followup_action: _Optional[str] = ..., active_loop: _Optional[_Mapping[str, str]] = ..., latest_action_name: _Optional[str] = ..., stack: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ...) -> None: ...

class Intent(_message.Message):
    __slots__ = ["string_value", "dict_value"]
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    DICT_VALUE_FIELD_NUMBER: _ClassVar[int]
    string_value: str
    dict_value: _struct_pb2.Struct
    def __init__(self, string_value: _Optional[str] = ..., dict_value: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class Entity(_message.Message):
    __slots__ = ["string_value", "dict_value"]
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    DICT_VALUE_FIELD_NUMBER: _ClassVar[int]
    string_value: str
    dict_value: _struct_pb2.Struct
    def __init__(self, string_value: _Optional[str] = ..., dict_value: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class Action(_message.Message):
    __slots__ = ["string_value", "dict_value"]
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    DICT_VALUE_FIELD_NUMBER: _ClassVar[int]
    string_value: str
    dict_value: _struct_pb2.Struct
    def __init__(self, string_value: _Optional[str] = ..., dict_value: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class Domain(_message.Message):
    __slots__ = ["config", "session_config", "intents", "entities", "slots", "responses", "actions", "forms", "e2e_actions"]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    SESSION_CONFIG_FIELD_NUMBER: _ClassVar[int]
    INTENTS_FIELD_NUMBER: _ClassVar[int]
    ENTITIES_FIELD_NUMBER: _ClassVar[int]
    SLOTS_FIELD_NUMBER: _ClassVar[int]
    RESPONSES_FIELD_NUMBER: _ClassVar[int]
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    FORMS_FIELD_NUMBER: _ClassVar[int]
    E2E_ACTIONS_FIELD_NUMBER: _ClassVar[int]
    config: _struct_pb2.Struct
    session_config: _struct_pb2.Struct
    intents: _containers.RepeatedCompositeFieldContainer[Intent]
    entities: _containers.RepeatedCompositeFieldContainer[Entity]
    slots: _struct_pb2.Struct
    responses: _struct_pb2.Struct
    actions: _containers.RepeatedCompositeFieldContainer[Action]
    forms: _struct_pb2.Struct
    e2e_actions: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    def __init__(self, config: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., session_config: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., intents: _Optional[_Iterable[_Union[Intent, _Mapping]]] = ..., entities: _Optional[_Iterable[_Union[Entity, _Mapping]]] = ..., slots: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., responses: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., actions: _Optional[_Iterable[_Union[Action, _Mapping]]] = ..., forms: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., e2e_actions: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ...) -> None: ...

class WebhookRequest(_message.Message):
    __slots__ = ["next_action", "sender_id", "tracker", "domain", "version", "domain_digest"]
    NEXT_ACTION_FIELD_NUMBER: _ClassVar[int]
    SENDER_ID_FIELD_NUMBER: _ClassVar[int]
    TRACKER_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    DOMAIN_DIGEST_FIELD_NUMBER: _ClassVar[int]
    next_action: str
    sender_id: str
    tracker: Tracker
    domain: Domain
    version: str
    domain_digest: str
    def __init__(self, next_action: _Optional[str] = ..., sender_id: _Optional[str] = ..., tracker: _Optional[_Union[Tracker, _Mapping]] = ..., domain: _Optional[_Union[Domain, _Mapping]] = ..., version: _Optional[str] = ..., domain_digest: _Optional[str] = ...) -> None: ...

class WebhookResponse(_message.Message):
    __slots__ = ["events", "responses"]
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    RESPONSES_FIELD_NUMBER: _ClassVar[int]
    events: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    responses: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    def __init__(self, events: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ..., responses: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ...) -> None: ...
