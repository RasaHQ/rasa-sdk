import asyncio
import os
import shutil
import random
import string
import time

from typing import Any, Dict, List, Text, Optional, Generator

import pytest
from rasa_sdk import Action
from rasa_sdk.executor import ActionExecutor, CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.interfaces import Tracker
from tests.conftest import SubclassTestActionA, SubclassTestActionB

TEST_PACKAGE_BASE = "tests/executor_test_packages"

ACTION_TEMPLATE = """
from rasa_sdk import Action

class {class_name}(Action):
    def name(self):
        return "{action_name}"

    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message("{message}")
        return []
"""


def _write_action_file(
    package_path: Text,
    file_name: Text,
    class_name: Text,
    action_name: Text,
    message: Optional[Text] = None,
) -> None:
    with open(os.path.join(package_path, file_name), "w") as f:
        f.write(
            ACTION_TEMPLATE.format(
                class_name=class_name, action_name=action_name, message=message
            )
        )


@pytest.mark.parametrize(
    "noevent", [1, ["asd"], "asd", 3.2, None, {"event_without_event_property": 4}]
)
def test_event_validation_fails_on_odd_things(noevent):
    assert ActionExecutor.validate_events([noevent], "myaction") == []


def test_event_validation_accepts_dicts_with_event():
    assert ActionExecutor.validate_events([{"event": "user"}], "myaction") == [
        {"event": "user"}
    ]


def test_deprecated_utter_elements():
    dispatcher = CollectingDispatcher()
    with pytest.warns(FutureWarning):
        dispatcher.utter_elements(1, 2, 3)

    assert dispatcher.messages[0] == {
        "text": None,
        "buttons": [],
        "elements": [1, 2, 3],
        "custom": {},
        "template": None,
        "response": None,
        "image": None,
        "attachment": None,
    }


def test_utter_message_with_template_param():
    dispatcher = CollectingDispatcher()
    with pytest.warns(FutureWarning):
        dispatcher.utter_message(template="utter_greet")

    assert dispatcher.messages[0] == {
        "text": None,
        "buttons": [],
        "elements": [],
        "custom": {},
        "template": "utter_greet",
        "response": "utter_greet",
        "image": None,
        "attachment": None,
    }


def test_utter_message_with_response_param():
    dispatcher = CollectingDispatcher()
    dispatcher.utter_message(response="utter_greet")

    assert dispatcher.messages[0] == {
        "text": None,
        "buttons": [],
        "elements": [],
        "custom": {},
        "template": "utter_greet",
        "response": "utter_greet",
        "image": None,
        "attachment": None,
    }


@pytest.fixture()
def package_path() -> Generator[Text, None, Text]:
    # Create an empty directory somewhere reached by the Python import search
    # paths
    name = "".join(random.choice(string.ascii_lowercase) for _ in range(10))
    package_path = os.path.join(TEST_PACKAGE_BASE, name)

    # Ensure package dir is clean
    shutil.rmtree(package_path, ignore_errors=True)
    os.makedirs(package_path)
    yield package_path

    # Cleanup
    shutil.rmtree(package_path, ignore_errors=True)


@pytest.fixture()
def executor() -> ActionExecutor:
    return ActionExecutor()


@pytest.fixture()
def dispatcher() -> CollectingDispatcher:
    return CollectingDispatcher()


def test_load_action_from_init(executor: ActionExecutor, package_path: Text):
    # Actions should be loaded from packages
    _write_action_file(package_path, "__init__.py", "InitAction", "init_action")
    executor.register_package(package_path.replace("/", "."))

    assert "init_action" in executor.actions


def test_load_submodules_in_package(executor: ActionExecutor, package_path: Text):
    # If there's submodules inside a package, they should be picked up correctly
    _write_action_file(package_path, "__init__.py", "Action1", "action1")
    _write_action_file(package_path, "a1.py", "Action2", "action2")
    _write_action_file(package_path, "a2.py", "Action3", "action3")

    executor.register_package(package_path.replace("/", "."))

    for name in ["action1", "action2", "action3"]:
        assert name in executor.actions


def test_load_submodules_in_namespace_package(
    executor: ActionExecutor, package_path: Text
):
    # If there's submodules inside a namespace package (a package without
    # __init__.py), they should be picked up correctly
    _write_action_file(package_path, "foo.py", "FooAction", "foo_action")
    _write_action_file(package_path, "bar.py", "BarAction", "bar_action")

    executor.register_package(package_path.replace("/", "."))

    for name in ["foo_action", "bar_action"]:
        assert name in executor.actions


def test_load_module_directly(executor: ActionExecutor, package_path: Text):
    _write_action_file(
        package_path, "test_module.py", "TestModuleAction", "test_module_action"
    )

    # Load a module directly, not a package. This is equivalent to loading
    # "action" when there's an "action.py" file in the module search path.
    executor.register_package(package_path.replace("/", ".") + ".test_module")

    assert "test_module_action" in executor.actions


async def test_reload_module(
    executor: ActionExecutor, dispatcher: CollectingDispatcher, package_path: Text
):
    action_class = "MyAction"
    action_file = "my_action.py"
    action_name = "my_action"

    _write_action_file(
        package_path, action_file, action_class, action_name, message="foobar"
    )

    executor.register_package(package_path.replace("/", "."))

    action_v1 = executor.actions.get(action_name)
    assert action_v1

    await action_v1(dispatcher, None, None)

    assert dispatcher.messages[0] == {
        "text": "foobar",
        "buttons": [],
        "elements": [],
        "custom": {},
        "template": None,
        "response": None,
        "image": None,
        "attachment": None,
    }

    # Write the action file again, but change its contents
    _write_action_file(
        package_path, action_file, action_class, action_name, message="hello!"
    )

    # Manually set the file's timestamp 10 seconds into the future, otherwise
    # Python will load the class already compiled in __pycache__, which is the
    # previous version.
    mod_time = time.time() + 10
    os.utime(os.path.join(package_path, action_file), times=(mod_time, mod_time))

    # Reload modules
    executor.reload()
    dispatcher.messages.clear()

    action_v2 = executor.actions.get(action_name)
    assert action_v2

    await action_v2(dispatcher, None, None)

    # The message should have changed
    assert dispatcher.messages[0] == {
        "text": "hello!",
        "buttons": [],
        "elements": [],
        "custom": {},
        "template": None,
        "response": None,
        "image": None,
        "attachment": None,
    }


def test_load_subclasses(executor: ActionExecutor):
    executor.register_action(SubclassTestActionB)
    assert list(executor.actions) == ["subclass_test_action_b"]

    executor.register_action(SubclassTestActionA)
    assert sorted(list(executor.actions)) == [
        "subclass_test_action_a",
        "subclass_test_action_b",
    ]


async def test_reload_discovers_new_modules(
    executor: ActionExecutor, dispatcher: CollectingDispatcher, package_path: Text
):
    """Test that reload discovers newly created module files."""
    # Initially register package with one action
    _write_action_file(
        package_path, "action1.py", "Action1", "action_1", message="action 1"
    )

    executor.register_package(package_path.replace("/", "."))

    assert "action_1" in executor.actions
    assert "action_2" not in executor.actions

    # Create a new action file after registration
    _write_action_file(
        package_path, "action2.py", "Action2", "action_2", message="action 2"
    )

    # Set the file's timestamp into the future to ensure it's detected
    mod_time = time.time() + 10
    os.utime(os.path.join(package_path, "action2.py"), times=(mod_time, mod_time))

    # Reload should discover the new module
    executor.reload()

    # Both actions should now be registered
    assert "action_1" in executor.actions
    assert "action_2" in executor.actions

    # Test that the new action works
    action_2 = executor.actions.get("action_2")
    assert action_2

    await action_2(dispatcher, None, None)

    assert dispatcher.messages[0]["text"] == "action 2"


async def test_reload_discovers_new_modules_in_namespace_package(
    executor: ActionExecutor, dispatcher: CollectingDispatcher, package_path: Text
):
    """Test that reload discovers newly created modules in namespace packages."""
    # Start with a namespace package (no __init__.py) with one module
    _write_action_file(package_path, "foo.py", "FooAction", "foo_action", message="foo")

    executor.register_package(package_path.replace("/", "."))

    # Get initial action count
    initial_action_count = len(executor.actions)
    assert "foo_action" in executor.actions

    # Add a new module to the namespace package
    _write_action_file(package_path, "baz.py", "BazAction", "baz_action", message="baz")

    # Set timestamp into the future
    mod_time = time.time() + 10
    os.utime(os.path.join(package_path, "baz.py"), times=(mod_time, mod_time))

    # Reload should discover the new module
    executor.reload()

    # Action count should increase by 1
    assert len(executor.actions) == initial_action_count + 1
    assert "foo_action" in executor.actions
    assert "baz_action" in executor.actions

    # Test that the new action works
    action = executor.actions.get("baz_action")
    assert action

    await action(dispatcher, None, None)
    assert dispatcher.messages[0]["text"] == "baz"


def test_reload_tracks_registered_packages(
    executor: ActionExecutor, package_path: Text
):
    """Test that registered packages are tracked correctly."""
    _write_action_file(
        package_path, "action1.py", "Action1", "action_1", message="action 1"
    )

    package_name = package_path.replace("/", ".")
    executor.register_package(package_name)

    # Check that package is tracked
    assert package_name in executor._registered_packages


async def test_reload_with_modified_and_new_modules(
    executor: ActionExecutor, dispatcher: CollectingDispatcher, package_path: Text
):
    """Test that reload handles both modified and newly created modules."""
    # Start with one action using a unique name
    _write_action_file(
        package_path,
        "mod_action.py",
        "ModifiedAction",
        "modified_action",
        message="original",
    )

    executor.register_package(package_path.replace("/", "."))

    # Get initial action count
    initial_action_count = len(executor.actions)

    # Verify initial state
    assert "modified_action" in executor.actions
    assert "brand_new_action" not in executor.actions

    # Modify the existing action
    _write_action_file(
        package_path,
        "mod_action.py",
        "ModifiedAction",
        "modified_action",
        message="modified",
    )

    # Create a new action with a unique name
    _write_action_file(
        package_path,
        "new_action.py",
        "BrandNewAction",
        "brand_new_action",
        message="new action",
    )

    # Set timestamps into the future
    mod_time = time.time() + 10
    for file in ["mod_action.py", "new_action.py"]:
        os.utime(os.path.join(package_path, file), times=(mod_time, mod_time))

    # Reload should handle both cases
    executor.reload()

    # Action count should increase by 1 (one new action added)
    assert len(executor.actions) == initial_action_count + 1

    # Both actions should be registered
    assert "modified_action" in executor.actions
    assert "brand_new_action" in executor.actions

    # Test modified action
    action_1 = executor.actions.get("modified_action")
    await action_1(dispatcher, None, None)
    assert dispatcher.messages[0]["text"] == "modified"

    dispatcher.messages.clear()

    # Test new action
    action_2 = executor.actions.get("brand_new_action")
    await action_2(dispatcher, None, None)
    assert dispatcher.messages[0]["text"] == "new action"


# ---------------------------------------------------------------------------
# Helpers shared by the streaming tests
# ---------------------------------------------------------------------------

MINIMAL_ACTION_CALL = {
    "next_action": "action_streaming",
    "tracker": {
        "sender_id": "test",
        "slots": {},
        "latest_message": {},
        "events": [],
        "paused": False,
        "followup_action": None,
        "active_loop": {},
        "active_form": {},
        "latest_action_name": None,
        "stack": [],
        "user_id": None,
    },
    "domain": {
        "intents": [],
        "entities": [],
        "slots": {},
        "responses": {},
        "actions": [],
        "forms": {},
    },
}


class StreamingAction(Action):
    """Action that exercises the full streaming API."""

    def name(self) -> Text:
        return "action_streaming"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:
        await dispatcher.stream_start()
        await dispatcher.stream_chunk(text="Hello ")
        await dispatcher.stream_chunk(text="world")
        await dispatcher.stream_chunk(
            text="Pick one",
            buttons=[{"title": "A", "payload": "/a"}, {"title": "B", "payload": "/b"}],
        )
        await dispatcher.stream_end()
        return []


@pytest.fixture()
def streaming_executor() -> ActionExecutor:
    executor = ActionExecutor()
    executor.register_action(StreamingAction)
    return executor


async def _drain_queue(sink: asyncio.Queue) -> List[Dict]:
    """Collect all items currently in *q* without blocking."""
    items = []
    while not sink.empty():
        items.append(await sink.get())
    return items


async def test_stream_chunk_text_only_accumulates():
    dispatcher = CollectingDispatcher()
    await dispatcher.stream_chunk(text="Hello")
    assert dispatcher._stream_accumulated_chunks == [{"text": "Hello"}]


async def test_stream_chunk_implicitly_starts_stream_when_stream_start_not_called():
    dispatcher = CollectingDispatcher()
    assert not dispatcher.is_streaming_active
    await dispatcher.stream_chunk(text="implicit")
    assert dispatcher.is_streaming_active
    assert dispatcher._stream_accumulated_chunks == [{"text": "implicit"}]


async def test_stream_chunk_implicit_start_emits_stream_start_event_to_sink():
    """When stream_chunk() triggers an implicit stream_start, the sink must
    receive stream_start before stream_chunk so the protocol ordering is correct."""
    sink: asyncio.Queue = asyncio.Queue()
    dispatcher = CollectingDispatcher()
    dispatcher._stream_sink = sink.put
    await dispatcher.stream_chunk(text="hi")
    events = [sink.get_nowait() for _ in range(sink.qsize())]
    assert events[0] == {"event": "stream_start"}
    assert events[1] == {"event": "stream_chunk", "text": "hi"}


async def test_stream_chunk_rich_content_accumulates():
    dispatcher = CollectingDispatcher()
    buttons = [{"title": "Yes", "payload": "/yes"}]
    await dispatcher.stream_chunk(image="https://example.com/img.png", buttons=buttons)
    assert dispatcher._stream_accumulated_chunks == [
        {"image": "https://example.com/img.png", "buttons": buttons}
    ]


async def test_stream_chunk_json_message_forwarded_to_sink_as_custom():
    d = CollectingDispatcher()
    sink: asyncio.Queue = asyncio.Queue()
    d._stream_sink = sink.put

    payload = {"type": "card", "title": "Hello"}
    await d.stream_start()
    await sink.get()  # consume stream_start
    await d.stream_chunk(json_message=payload)

    event = await sink.get()
    assert event == {"event": "stream_chunk", "custom": payload}


async def test_stream_end_no_sink_json_message_replayed_via_utter_message():
    """On the fallback path, custom JSON ends up in the message dict's
    'custom' field — the same place utter_message puts it."""
    d = CollectingDispatcher()
    await d.stream_start()
    await d.stream_chunk(json_message={"type": "card"})
    await d.stream_end()

    assert len(d.messages) == 1
    assert d.messages[0]["custom"] == {"type": "card"}


async def test_stream_chunk_text_and_rich_accumulates():
    dispatcher = CollectingDispatcher()
    buttons = [{"title": "OK", "payload": "/ok"}]
    await dispatcher.stream_chunk(text="Choose:", buttons=buttons)
    assert dispatcher._stream_accumulated_chunks == [
        {"text": "Choose:", "buttons": buttons}
    ]


async def test_stream_chunk_omits_none_and_empty_fields():
    """Fields passed as None should be omitted from the payload."""
    dispatcher = CollectingDispatcher()
    await dispatcher.stream_chunk(text="hi", image=None, buttons=None)
    assert dispatcher._stream_accumulated_chunks == [{"text": "hi"}]


@pytest.mark.parametrize("forbidden_key", ["template", "response"])
async def test_stream_chunk_raises_on_template_or_response_kwarg(forbidden_key):
    """template/response must be rejected, not silently forwarded in the payload."""
    dispatcher = CollectingDispatcher()
    with pytest.raises(ValueError, match=forbidden_key):
        await dispatcher.stream_chunk(**{forbidden_key: "utter_greet"})


async def test_stream_chunk_raises_when_both_template_and_response_passed():
    dispatcher = CollectingDispatcher()
    with pytest.raises(ValueError):
        await dispatcher.stream_chunk(template="utter_greet", response="utter_greet")


async def test_stream_chunk_multiple_chunks_accumulate_in_order():
    dispatcher = CollectingDispatcher()
    await dispatcher.stream_chunk(text="one")
    await dispatcher.stream_chunk(text="two")
    await dispatcher.stream_chunk(text="three")
    assert [c["text"] for c in dispatcher._stream_accumulated_chunks] == [
        "one",
        "two",
        "three",
    ]


async def test_stream_start_resets_accumulator():
    dispatcher = CollectingDispatcher()
    await dispatcher.stream_start()
    await dispatcher.stream_chunk(text="stale")
    assert dispatcher._stream_accumulated_chunks == [{"text": "stale"}]
    await dispatcher.stream_start()  # second call should clear stale chunks
    assert dispatcher._stream_accumulated_chunks == []
    assert dispatcher.is_streaming_active  # flag stays True after the reset


async def test_stream_end_no_sink_replays_each_chunk_as_utter_message():
    dispatcher = CollectingDispatcher()
    await dispatcher.stream_start()
    await dispatcher.stream_chunk(text="Hello")
    await dispatcher.stream_chunk(
        text="Pick one",
        buttons=[{"title": "A", "payload": "/a"}],
    )
    await dispatcher.stream_end()

    assert len(dispatcher.messages) == 2
    assert dispatcher.messages[0]["text"] == "Hello"
    assert dispatcher.messages[1]["text"] == "Pick one"
    assert dispatcher.messages[1]["buttons"] == [{"title": "A", "payload": "/a"}]


async def test_is_streaming_active_reflects_stream_lifecycle():
    dispatcher = CollectingDispatcher()
    assert not dispatcher.is_streaming_active  # nothing started yet
    await dispatcher.stream_start()
    assert (
        dispatcher.is_streaming_active
    )  # True immediately after stream_start, even with no chunks
    await dispatcher.stream_chunk(text="Hi")
    assert dispatcher.is_streaming_active  # still True with chunks accumulated
    await dispatcher.stream_end()
    assert not dispatcher.is_streaming_active  # False after stream_end


async def test_stream_end_no_sink_empty_accumulator_adds_no_messages():
    dispatcher = CollectingDispatcher()
    await dispatcher.stream_start()
    await dispatcher.stream_end()
    assert dispatcher.messages == []


async def test_stream_start_with_sink_emits_event():
    dispatcher = CollectingDispatcher()
    sink: asyncio.Queue = asyncio.Queue()
    dispatcher._stream_sink = sink.put

    await dispatcher.stream_start()
    assert await sink.get() == {"event": "stream_start"}


async def test_stream_chunk_with_sink_forwards_immediately():
    dispatcher = CollectingDispatcher()
    sink: asyncio.Queue = asyncio.Queue()
    dispatcher._stream_sink = sink.put

    await dispatcher.stream_start()
    await sink.get()  # consume stream_start
    await dispatcher.stream_chunk(text="Hi", image="https://example.com/img.png")

    event = await sink.get()
    assert event == {
        "event": "stream_chunk",
        "text": "Hi",
        "image": "https://example.com/img.png",
    }


async def test_stream_end_with_sink_emits_event_and_no_utter_message():
    dispatcher = CollectingDispatcher()
    sink: asyncio.Queue = asyncio.Queue()
    dispatcher._stream_sink = sink.put

    await dispatcher.stream_start()
    await sink.get()  # consume stream_start
    await dispatcher.stream_chunk(text="Hello")
    await sink.get()  # consume stream_chunk
    await dispatcher.stream_end()

    assert await sink.get() == {"event": "stream_end"}
    assert dispatcher.messages == []  # utter_message NOT called on streaming path


async def test_stream_full_lifecycle_with_sink_emits_all_events():
    dispatcher = CollectingDispatcher()
    sink: asyncio.Queue = asyncio.Queue()
    dispatcher._stream_sink = sink.put

    await dispatcher.stream_start()
    await dispatcher.stream_chunk(text="Hello ")
    await dispatcher.stream_chunk(
        text="world", buttons=[{"title": "OK", "payload": "/ok"}]
    )
    await dispatcher.stream_end()

    events = await _drain_queue(sink)
    assert events[0] == {"event": "stream_start"}
    assert events[1] == {"event": "stream_chunk", "text": "Hello "}
    assert events[2] == {
        "event": "stream_chunk",
        "text": "world",
        "buttons": [{"title": "OK", "payload": "/ok"}],
    }
    assert events[3] == {"event": "stream_end"}


async def test_stream_full_lifecycle_no_sink_produces_utter_messages():
    dispatcher = CollectingDispatcher()
    await dispatcher.stream_start()
    await dispatcher.stream_chunk(text="Hello ")
    await dispatcher.stream_chunk(image="https://example.com/img.png")
    await dispatcher.stream_end()

    assert len(dispatcher.messages) == 2
    assert dispatcher.messages[0]["text"] == "Hello "
    assert dispatcher.messages[1]["image"] == "https://example.com/img.png"


# ---------------------------------------------------------------------------
# ActionExecutor.run() — streaming integration
# ---------------------------------------------------------------------------


async def test_executor_run_without_sink_streaming_fallback(
    streaming_executor: ActionExecutor,
):
    """Without a sink, stream_end flushes chunks as utter_messages."""
    result = await streaming_executor.run(MINIMAL_ACTION_CALL)
    assert result is not None
    # Three stream_chunk calls → three utter_message entries in responses
    assert len(result.responses) == 3
    assert result.responses[0]["text"] == "Hello "
    assert result.responses[1]["text"] == "world"
    assert result.responses[2]["text"] == "Pick one"
    assert result.responses[2]["buttons"] == [
        {"title": "A", "payload": "/a"},
        {"title": "B", "payload": "/b"},
    ]


async def test_executor_run_with_sink_streams_events(
    streaming_executor: ActionExecutor,
):
    """With a sink, chunk events arrive in the queue as the action runs."""
    sink: asyncio.Queue = asyncio.Queue()
    result = await streaming_executor.run(MINIMAL_ACTION_CALL, sink=sink)

    events = await _drain_queue(sink)
    event_types = [e["event"] for e in events]

    assert event_types == [
        "stream_start",
        "stream_chunk",
        "stream_chunk",
        "stream_chunk",
        "stream_end",
        "stream_done",
    ]
    assert events[1]["text"] == "Hello "
    assert events[2]["text"] == "world"
    assert events[3]["text"] == "Pick one"
    assert events[3]["buttons"] == [
        {"title": "A", "payload": "/a"},
        {"title": "B", "payload": "/b"},
    ]
    assert events[-1]["result"] is result


async def test_executor_run_with_sink_stream_done_carries_result(
    streaming_executor: ActionExecutor,
):
    sink: asyncio.Queue = asyncio.Queue()
    result = await streaming_executor.run(MINIMAL_ACTION_CALL, sink=sink)
    events = await _drain_queue(sink)
    done = next(e for e in events if e["event"] == "stream_done")
    assert done["result"] is result


async def test_run_streaming_delegates_to_run(streaming_executor: ActionExecutor):
    """`run_streaming` is a thin wrapper; the queue events are identical."""
    sink_a: asyncio.Queue = asyncio.Queue()
    sink_b: asyncio.Queue = asyncio.Queue()

    await streaming_executor.run(MINIMAL_ACTION_CALL, sink=sink_a)
    await streaming_executor.run_streaming(MINIMAL_ACTION_CALL, sink=sink_b)

    events_a = [e["event"] for e in await _drain_queue(sink_a)]
    events_b = [e["event"] for e in await _drain_queue(sink_b)]
    assert events_a == events_b


async def test_executor_run_puts_stream_error_in_sink_when_action_raises(
    streaming_executor: ActionExecutor,
):
    """run() must place stream_error in the sink before re-raising so concurrent
    consumers on the sink queue are never left blocked."""

    class _BoomAction(Action):
        def name(self) -> Text:
            return "action_boom"

        async def run(self, dispatcher, tracker, domain):
            raise RuntimeError("action exploded")

    streaming_executor.register_action(_BoomAction)
    action_call = {**MINIMAL_ACTION_CALL, "next_action": "action_boom"}
    sink: asyncio.Queue = asyncio.Queue()

    with pytest.raises(RuntimeError, match="action exploded"):
        await streaming_executor.run(action_call, sink=sink)

    events = await _drain_queue(sink)
    event_types = [e["event"] for e in events]
    assert "stream_error" in event_types
    error_event = next(e for e in events if e["event"] == "stream_error")
    assert isinstance(error_event["exception"], RuntimeError)


# ---------------------------------------------------------------------------
# Auto-close guard: executor calls stream_end() if action forgets
# ---------------------------------------------------------------------------


class _MissingStreamEndAction(Action):
    """Action that opens a stream but never calls stream_end()."""

    def name(self) -> Text:
        return "action_missing_stream_end"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Dict[Text, Any]]:
        await dispatcher.stream_start()
        await dispatcher.stream_chunk(text="Hello")
        await dispatcher.stream_chunk(buttons=[{"title": "Yes", "payload": "/yes"}])
        # stream_end() intentionally omitted
        return []


@pytest.fixture()
def missing_end_executor() -> ActionExecutor:
    executor = ActionExecutor()
    executor.register_action(_MissingStreamEndAction)
    return executor


_MISSING_END_ACTION_CALL = {
    **MINIMAL_ACTION_CALL,
    "next_action": "action_missing_stream_end",
}


async def test_executor_auto_closes_stream_when_stream_end_not_called_no_sink(
    missing_end_executor: ActionExecutor,
):
    """Without a sink the accumulated chunks are still flushed as utter_messages."""
    result = await missing_end_executor.run(_MISSING_END_ACTION_CALL)
    assert result is not None
    assert len(result.responses) == 2
    assert result.responses[0]["text"] == "Hello"
    assert result.responses[1]["buttons"] == [{"title": "Yes", "payload": "/yes"}]


async def test_executor_auto_closes_stream_when_stream_end_not_called_with_sink(
    missing_end_executor: ActionExecutor,
):
    """With a sink the stream_end event is emitted automatically."""
    sink: asyncio.Queue = asyncio.Queue()
    await missing_end_executor.run(_MISSING_END_ACTION_CALL, sink=sink)

    events = await _drain_queue(sink)
    event_types = [e["event"] for e in events]
    assert "stream_end" in event_types
    assert "stream_done" in event_types
    assert event_types.index("stream_end") < event_types.index("stream_done")


async def test_executor_auto_close_logs_warning(
    missing_end_executor: ActionExecutor,
    caplog: pytest.LogCaptureFixture,
):
    """A warning is logged so action authors can find and fix the bug."""
    import logging

    with caplog.at_level(logging.WARNING, logger="rasa_sdk.executor"):
        await missing_end_executor.run(_MISSING_END_ACTION_CALL)

    assert any("stream_end" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Cancellation / barge-in: cancel_stream, acknowledge_heard_chunks, stream_end
# ---------------------------------------------------------------------------


async def test_cancel_stream_sets_flag():
    dispatcher = CollectingDispatcher()
    assert not dispatcher.is_streaming_cancelled
    dispatcher.cancel_stream()
    assert dispatcher.is_streaming_cancelled


async def test_stream_chunk_dropped_after_cancel():
    """Chunks emitted after cancel_stream() are silently ignored."""
    dispatcher = CollectingDispatcher()
    await dispatcher.stream_start()
    await dispatcher.stream_chunk(text="before")
    dispatcher.cancel_stream()
    await dispatcher.stream_chunk(text="after cancel")

    assert dispatcher._stream_accumulated_chunks == [{"text": "before"}]


async def test_stream_chunk_does_not_forward_to_sink_after_cancel():
    sink: asyncio.Queue = asyncio.Queue()
    dispatcher = CollectingDispatcher()
    dispatcher._stream_sink = sink.put
    await dispatcher.stream_start()
    await sink.get()  # consume stream_start
    await dispatcher.stream_chunk(text="sent")
    await sink.get()  # consume stream_chunk
    dispatcher.cancel_stream()
    await dispatcher.stream_chunk(text="dropped")

    assert sink.empty()


async def test_stream_delivered_chunks_tracks_forwarded_chunks():
    """Only chunks forwarded to the sink appear in _stream_delivered_chunks."""
    sink: asyncio.Queue = asyncio.Queue()
    dispatcher = CollectingDispatcher()
    dispatcher._stream_sink = sink.put
    await dispatcher.stream_start()
    await dispatcher.stream_chunk(text="A")
    await dispatcher.stream_chunk(text="B")
    dispatcher.cancel_stream()
    await dispatcher.stream_chunk(text="C")  # dropped

    assert [c["text"] for c in dispatcher._stream_delivered_chunks] == ["A", "B"]


async def test_acknowledge_heard_chunks_slices_delivered():
    dispatcher = CollectingDispatcher()
    dispatcher._stream_delivered_chunks = [
        {"text": "A"},
        {"text": "B"},
        {"text": "C"},
    ]
    dispatcher.acknowledge_heard_chunks(last_heard_chunk_index=1)
    assert dispatcher._stream_heard_chunks == [{"text": "A"}, {"text": "B"}]


async def test_acknowledge_heard_chunks_nothing_heard():
    dispatcher = CollectingDispatcher()
    dispatcher._stream_delivered_chunks = [{"text": "A"}, {"text": "B"}]
    dispatcher.acknowledge_heard_chunks(last_heard_chunk_index=-1)
    assert dispatcher._stream_heard_chunks == []


async def test_stream_end_cancelled_does_not_replay_chunks_via_utter_message():
    """On the streaming path, stream_end() never calls utter_message() regardless
    of cancellation state — the voice channel owns tracker storage for streamed
    content, not rasa-sdk."""
    sink: asyncio.Queue = asyncio.Queue()
    dispatcher = CollectingDispatcher()
    dispatcher._stream_sink = sink.put
    await dispatcher.stream_start()
    await dispatcher.stream_chunk(text="heard 1")
    await dispatcher.stream_chunk(text="heard 2")
    await dispatcher.stream_chunk(text="not heard")
    dispatcher.acknowledge_heard_chunks(last_heard_chunk_index=1)
    dispatcher.cancel_stream()
    await dispatcher.stream_end()

    assert dispatcher.messages == []  # nothing replayed; voice channel handles it


async def test_stream_end_cancelled_without_ack_also_does_not_replay():
    """Same as above: even without an ack, no utter_message() on streaming path."""
    sink: asyncio.Queue = asyncio.Queue()
    dispatcher = CollectingDispatcher()
    dispatcher._stream_sink = sink.put
    await dispatcher.stream_start()
    await dispatcher.stream_chunk(text="delivered 1")
    await dispatcher.stream_chunk(text="delivered 2")
    dispatcher.cancel_stream()
    await dispatcher.stream_end()

    assert dispatcher.messages == []


async def test_stream_start_resets_cancellation_state():
    """A second stream_start() clears cancellation so a new sequence can begin."""
    dispatcher = CollectingDispatcher()
    await dispatcher.stream_start()
    dispatcher.cancel_stream()
    dispatcher.acknowledge_heard_chunks(0)
    assert dispatcher.is_streaming_cancelled
    assert dispatcher._stream_heard_chunks is not None

    await dispatcher.stream_start()  # second sequence begins
    assert not dispatcher.is_streaming_cancelled
    assert dispatcher._stream_heard_chunks is None
    assert dispatcher._stream_delivered_chunks == []
