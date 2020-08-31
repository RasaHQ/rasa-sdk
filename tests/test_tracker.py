import pytest

from rasa_sdk import Tracker
from rasa_sdk.events import ActionExecuted, UserUttered, ActionReverted, SlotSet
from rasa_sdk.interfaces import ACTION_LISTEN_NAME
from typing import List, Dict, Text, Any


def user_uttered(text: Text, confidence: float) -> UserUttered:
    parse_data = {"intent": {"name": text, "confidence": confidence}}
    return UserUttered(text="Random", parse_data=parse_data)


def get_tracker(events: List[Dict[Text, Any]]) -> Tracker:
    return Tracker.from_dict({"sender_id": "sender", "events": events})


def test_latest_input_channel():
    tracker = get_tracker(
        [
            UserUttered("my message text", input_channel="superchat"),
            ActionExecuted("action_listen"),
        ]
    )

    assert tracker.get_latest_input_channel() == "superchat"


def test_get_last_event_for():
    events = [ActionExecuted("one"), user_uttered("two", 1)]

    tracker = get_tracker(events)

    assert tracker.get_last_event_for("action").get("name") == "one"


def test_get_last_event_for_with_skip():
    events = [ActionExecuted("one"), user_uttered("two", 1), ActionExecuted("three")]

    tracker = get_tracker(events)

    assert tracker.get_last_event_for("action", skip=1).get("name") == "one"


def test_get_last_event_for_with_exclude():
    events = [ActionExecuted("one"), user_uttered("two", 1), ActionExecuted("three")]

    tracker = get_tracker(events)

    assert tracker.get_last_event_for("action", exclude=["three"]).get("name") == "one"


def test_last_executed_has():
    events = [
        ActionExecuted("one"),
        user_uttered("two", 1),
        ActionExecuted(ACTION_LISTEN_NAME),
    ]

    tracker = get_tracker(events)

    assert tracker.last_executed_action_has("one") is True


def test_last_executed_has_not_name():
    events = [
        ActionExecuted("one"),
        user_uttered("two", 1),
        ActionExecuted(ACTION_LISTEN_NAME),
    ]

    tracker = get_tracker(events)

    assert tracker.last_executed_action_has("another") is False


@pytest.mark.parametrize(
    "events, expected_extracted_slots",
    [
        ([], {}),
        ([ActionExecuted("my_form")], {}),
        (
            [ActionExecuted("my_form"), SlotSet("my_slot", "some_value")],
            {"my_slot": "some_value"},
        ),
        (
            [
                ActionExecuted("my_form"),
                SlotSet("my_slot", "some_value"),
                SlotSet("some_other", "some_value2"),
            ],
            {"my_slot": "some_value", "some_other": "some_value2"},
        ),
        ([SlotSet("my_slot", "some_value"), ActionExecuted("my_form")], {},),
    ],
)
def test_get_extracted_slots(
    events: List[Dict[Text, Any]], expected_extracted_slots: Dict[Text, Any]
):
    tracker = get_tracker(events)
    tracker.active_loop = {"name": "my form"}
    assert tracker.form_slots_to_validate() == expected_extracted_slots


def test_get_extracted_slots_with_no_active_loop():
    events = [
        ActionExecuted("my_form"),
        SlotSet("my_slot", "some_value"),
        SlotSet("some_other", "some_value2"),
    ]
    tracker = get_tracker(events)

    assert tracker.form_slots_to_validate() == {}
