from typing import Any, Dict, List, Text

import pytest
from rasa_sdk.events import SlotSet

from rasa_sdk.interfaces import Tracker
from tests.conftest import get_stack


@pytest.mark.parametrize(
    "active_loop",
    [
        {},
        {"name": "some loop"},
        {"name": "some loop", "validate": True},
        {"name": "✏️", "rejected": False},
        {
            "name": "✏️",
            "validate": True,
            "trigger_message": {"intent": {}, "intent_ranking": []},
        },
    ],
)
def test_tracker_active_loop_parsing(active_loop: Dict):
    state = {"events": [], "sender_id": "old", "active_loop": active_loop}
    tracker = Tracker.from_dict(state)

    assert tracker.active_loop == active_loop


def test_deprecation_warning_active_form():
    form = {"name": "my form"}
    state = {"events": [], "sender_id": "old", "active_loop": form}
    tracker = Tracker.from_dict(state)

    with pytest.warns(DeprecationWarning):
        assert tracker.active_form == form


def test_parsing_of_trackers_with_old_active_form_field():
    form = {"name": "my form"}
    state = {"events": [], "sender_id": "old", "active_form": form}
    tracker = Tracker.from_dict(state)

    assert tracker.active_loop == form


def test_active_loop_in_tracker_state():
    form = {"name": "my form"}
    state = {"events": [], "sender_id": "old", "active_loop": form}
    tracker = Tracker.from_dict(state)

    assert tracker.current_state()["active_loop"] == form


def test_tracker_with_slots():
    form = {"name": "my form"}
    state = {"events": [], "sender_id": "old", "active_loop": form}
    tracker = Tracker.from_dict(state)

    tracker.add_slots([SlotSet("my slot", 5), SlotSet("my slot 2", None)])

    assert tracker.slots["my slot"] == 5
    assert tracker.slots["my slot 2"] is None


@pytest.mark.parametrize(
    "stack_state, dialogue_stack",
    [
        ({}, []),
        ({"stack": get_stack()}, get_stack()),
    ],
)
def test_stack_in_tracker_state(
    stack_state: Dict[Text, Any], dialogue_stack: List[Dict[Text, Any]]
):
    state = {"events": [], "sender_id": "old", "active_loop": {}, **stack_state}
    tracker = Tracker.from_dict(state)

    assert tracker.stack == dialogue_stack
    assert tracker.copy().stack == dialogue_stack
    assert tracker.current_state()["stack"] == dialogue_stack
