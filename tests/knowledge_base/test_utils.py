import pytest

from rasa_sdk import Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.knowledge_base.utils import (
    get_attribute_slots,
    reset_attribute_slots,
    get_object_name,
    SLOT_MENTION,
    SLOT_OBJECT_TYPE,
    SLOT_LAST_OBJECT,
    SLOT_LISTED_OBJECTS,
    SLOT_LAST_OBJECT_TYPE,
)


def test_get_attribute_slots():
    object_attributes = ["name", "cuisine", "price-range"]

    expected_attribute_slots = [
        {"name": "name", "value": "PastaBar"},
        {"name": "cuisine", "value": "Italian"},
    ]

    tracker = Tracker(
        "default",
        {"name": "PastaBar", "cuisine": "Italian"},
        {},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    attribute_slots = get_attribute_slots(tracker, object_attributes)

    for a in attribute_slots:
        assert a in expected_attribute_slots


def test_reset_attribute_slots():
    object_attributes = ["name", "cuisine", "price-range"]

    expected_reset_slots = [SlotSet("name", None), SlotSet("cuisine", None)]

    tracker = Tracker(
        "default",
        {"name": "PastaBar", "cuisine": "Italian"},
        {},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    reset_slots = reset_attribute_slots(tracker, object_attributes)

    for s in reset_slots:
        assert s in expected_reset_slots


@pytest.mark.parametrize(
    "slots,use_last_object_mention,expected_object_name",
    [
        (
            {
                SLOT_MENTION: "1",
                SLOT_OBJECT_TYPE: "restaurant",
                SLOT_LISTED_OBJECTS: ["Restaurant-1", "Restaurant-2", "Restaurant-3"],
                SLOT_LAST_OBJECT: None,
                SLOT_LAST_OBJECT_TYPE: "restaurant",
                "restaurant": None,
            },
            False,
            "Restaurant-1",
        ),
        (
            {
                SLOT_MENTION: None,
                SLOT_OBJECT_TYPE: "restaurant",
                SLOT_LISTED_OBJECTS: [],
                SLOT_LAST_OBJECT: None,
                SLOT_LAST_OBJECT_TYPE: None,
                "restaurant": "Restaurant-1",
            },
            False,
            "Restaurant-1",
        ),
        (
            {
                SLOT_MENTION: None,
                SLOT_OBJECT_TYPE: "restaurant",
                SLOT_LISTED_OBJECTS: [],
                SLOT_LAST_OBJECT: "Restaurant-2",
                SLOT_LAST_OBJECT_TYPE: "restaurant",
                "restaurant": None,
            },
            True,
            "Restaurant-2",
        ),
        (
            {
                SLOT_MENTION: None,
                SLOT_OBJECT_TYPE: "restaurant",
                SLOT_LISTED_OBJECTS: [],
                SLOT_LAST_OBJECT: "Restaurant-2",
                SLOT_LAST_OBJECT_TYPE: "restaurant",
                "restaurant": None,
            },
            False,
            None,
        ),
    ],
)
def test_get_object_name(slots, use_last_object_mention, expected_object_name):
    ordinal_mention_mapping = {
        "1": lambda l: l[0],
        "2": lambda l: l[1],
        "3": lambda l: l[2],
        "LAST": lambda l: l[-1],
    }

    tracker = Tracker("default", slots, {}, [], False, None, {}, "action_listen")

    actual_object_name = get_object_name(
        tracker, ordinal_mention_mapping, use_last_object_mention
    )

    assert actual_object_name == expected_object_name
