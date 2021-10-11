import pytest
import asyncio
from typing import Type, Text, Tuple, Dict, Any, List, Optional

from rasa_sdk import Tracker, ActionExecutionRejection
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet, ActiveLoop, EventType, UserUttered
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import (
    SlotMapping,
    FormAction,
    ValidationAction,
    REQUESTED_SLOT,
    LOOP_INTERRUPTED_KEY,
)


DEFAULT_DOMAIN = {
    "slots": {
        "some_other_slot": {
            "type": "any",
            "mappings": [SlotMapping.from_entity(entity="some_other_slot")],
        },
        "some_slot": {
            "type": "any",
            "mappings": [SlotMapping.from_entity(entity="some_slot")],
        },
    },
}


def test_extract_requested_slot_default():
    """Test default extraction of a slot value from entity with the same name"""
    form = FormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"entities": [{"entity": "some_slot", "value": "some_value"}]},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "some_slot": {
                "type": "any",
                "mappings": [
                    {
                        "type": "from_entity",
                        "entity": "some_slot",
                        "value": "some_value",
                    }
                ],
            },
        },
    }

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", domain
    )
    assert slot_values == {"some_slot": "some_value"}


def test_extract_requested_slot_from_entity_no_intent():
    """Test extraction of a slot value from entity with the different name
    and any intent
    """

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"entities": [{"entity": "some_entity", "value": "some_value"}]},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "some_slot": {
                "type": "any",
                "mappings": [SlotMapping.from_entity(entity="some_entity")],
            }
        }
    }

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", domain
    )
    assert slot_values == {"some_slot": "some_value"}


def test_extract_requested_slot_from_entity_with_intent():
    """Test extraction of a slot value from entity with the different name
    and certain intent
    """

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {
            "intent": {"name": "some_intent", "confidence": 1.0},
            "entities": [{"entity": "some_entity", "value": "some_value"}],
        },
        [],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "some_slot": {
                "type": "any",
                "mappings": [
                    SlotMapping.from_entity(entity="some_entity", intent="some_intent")
                ],
            }
        }
    }

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", domain
    )
    # check that the value was extracted for correct intent
    assert slot_values == {"some_slot": "some_value"}

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {
            "intent": {"name": "some_other_intent", "confidence": 1.0},
            "entities": [{"entity": "some_entity", "value": "some_value"}],
        },
        [],
        False,
        None,
        {},
        "action_listen",
    )

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", domain
    )
    # check that the value was not extracted for incorrect intent
    assert slot_values == {}


@pytest.mark.parametrize(
    "mapping_not_intent, mapping_intent, mapping_role, mapping_group, entities, intent, expected_slot_values",
    [
        (
            "some_intent",
            None,
            None,
            None,
            [{"entity": "some_entity", "value": "some_value"}],
            "some_intent",
            {},
        ),
        (
            None,
            "some_intent",
            None,
            None,
            [{"entity": "some_entity", "value": "some_value"}],
            "some_intent",
            {"some_slot": "some_value"},
        ),
        (
            "some_intent",
            None,
            None,
            None,
            [{"entity": "some_entity", "value": "some_value"}],
            "some_other_intent",
            {"some_slot": "some_value"},
        ),
        (
            None,
            None,
            "some_role",
            None,
            [{"entity": "some_entity", "value": "some_value"}],
            "some_intent",
            {},
        ),
        (
            None,
            None,
            "some_role",
            None,
            [{"entity": "some_entity", "value": "some_value", "role": "some_role"}],
            "some_intent",
            {"some_slot": "some_value"},
        ),
        (
            None,
            None,
            None,
            "some_group",
            [{"entity": "some_entity", "value": "some_value"}],
            "some_intent",
            {},
        ),
        (
            None,
            None,
            None,
            "some_group",
            [{"entity": "some_entity", "value": "some_value", "group": "some_group"}],
            "some_intent",
            {"some_slot": "some_value"},
        ),
        (
            None,
            None,
            "some_role",
            "some_group",
            [
                {
                    "entity": "some_entity",
                    "value": "some_value",
                    "group": "some_group",
                    "role": "some_role",
                }
            ],
            "some_intent",
            {"some_slot": "some_value"},
        ),
        (
            None,
            None,
            "some_role",
            "some_group",
            [{"entity": "some_entity", "value": "some_value", "role": "some_role"}],
            "some_intent",
            {},
        ),
        (
            None,
            None,
            None,
            None,
            [
                {
                    "entity": "some_entity",
                    "value": "some_value",
                    "group": "some_group",
                    "role": "some_role",
                }
            ],
            "some_intent",
            # nothing should be extracted, because entity contain role and group
            # but mapping expects them to be None
            {},
        ),
    ],
)
def test_extract_requested_slot_from_entity(
    mapping_not_intent: Optional[Text],
    mapping_intent: Optional[Text],
    mapping_role: Optional[Text],
    mapping_group: Optional[Text],
    entities: List[Dict[Text, Any]],
    intent: Text,
    expected_slot_values: Dict[Text, Text],
):
    """Test extraction of a slot value from entity with the different restrictions."""

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"intent": {"name": intent, "confidence": 1.0}, "entities": entities},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "some_slot": {
                "type": "any",
                "mappings": [
                    SlotMapping.from_entity(
                        entity="some_entity",
                        role=mapping_role,
                        group=mapping_group,
                        intent=mapping_intent,
                        not_intent=mapping_not_intent,
                    )
                ],
            },
        },
    }

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", domain
    )
    assert slot_values == expected_slot_values


def test_extract_requested_slot_from_intent():
    """Test extraction of a slot value from certain intent"""

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"intent": {"name": "some_intent", "confidence": 1.0}},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "some_slot": {
                "type": "any",
                "mappings": [
                    SlotMapping.from_intent(intent="some_intent", value="some_value")
                ],
            }
        }
    }

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", domain
    )
    # check that the value was extracted for correct intent
    assert slot_values == {"some_slot": "some_value"}

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"intent": {"name": "some_other_intent", "confidence": 1.0}},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", domain
    )
    # check that the value was not extracted for incorrect intent
    assert slot_values == {}


def test_extract_requested_slot_from_not_intent():
    """Test extraction of a slot value from certain intent"""

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"intent": {"name": "some_intent", "confidence": 1.0}},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "some_slot": {
                "type": "any",
                "mappings": [
                    SlotMapping.from_intent(
                        not_intent="some_intent", value="some_value"
                    )
                ],
            }
        }
    }

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", domain
    )
    # check that the value was extracted for correct intent
    assert slot_values == {}

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"intent": {"name": "some_other_intent", "confidence": 1.0}},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", domain
    )
    # check that the value was not extracted for incorrect intent
    assert slot_values == {"some_slot": "some_value"}


def test_extract_requested_slot_from_text_no_intent():
    """Test extraction of a slot value from text with any intent"""

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"text": "some_text"},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {"some_slot": {"type": "any", "mappings": [SlotMapping.from_text()]}}
    }

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", domain
    )
    assert slot_values == {"some_slot": "some_text"}


def test_extract_requested_slot_from_text_with_intent():
    """Test extraction of a slot value from text with certain intent"""

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"text": "some_text", "intent": {"name": "some_intent", "confidence": 1.0}},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "some_slot": {
                "type": "any",
                "mappings": [SlotMapping.from_text(intent="some_intent")],
            }
        }
    }

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", domain
    )
    # check that the value was extracted for correct intent
    assert slot_values == {"some_slot": "some_text"}

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {
            "text": "some_text",
            "intent": {"name": "some_other_intent", "confidence": 1.0},
        },
        [],
        False,
        None,
        {},
        "action_listen",
    )

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", domain
    )
    # check that the value was not extracted for incorrect intent
    assert slot_values == {}


def test_extract_requested_slot_from_text_with_not_intent():
    """Test extraction of a slot value from text with certain intent"""

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"text": "some_text", "intent": {"name": "some_intent", "confidence": 1.0}},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "some_slot": {
                "type": "any",
                "mappings": [SlotMapping.from_text(not_intent="some_intent")],
            }
        }
    }

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", domain
    )
    # check that the value was extracted for correct intent
    assert slot_values == {}

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {
            "text": "some_text",
            "intent": {"name": "some_other_intent", "confidence": 1.0},
        },
        [],
        False,
        None,
        {},
        "action_listen",
    )

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", domain
    )
    # check that the value was not extracted for incorrect intent
    assert slot_values == {"some_slot": "some_text"}


def test_extract_trigger_slots():
    """Test extraction of a slot value from trigger intent"""

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot"]

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {},
        {"intent": {"name": "trigger_intent", "confidence": 1.0}},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "some_slot": {
                "type": "any",
                "mappings": [
                    SlotMapping.from_trigger_intent(
                        intent="trigger_intent", value="some_value"
                    )
                ],
            }
        }
    }

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, domain)
    # check that the value was extracted for correct intent
    assert slot_values == {"some_slot": "some_value"}

    tracker = Tracker(
        "default",
        {},
        {"intent": {"name": "other_intent", "confidence": 1.0}},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, domain)
    # check that the value was not extracted for incorrect intent
    assert slot_values == {}

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {"intent": {"name": "trigger_intent", "confidence": 1.0}},
        [],
        False,
        None,
        {"name": "some_form", LOOP_INTERRUPTED_KEY: False, "rejected": False},
        "action_listen",
    )

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, domain)
    # check that the value was not extracted for correct intent
    assert slot_values == {}


def test_extract_other_slots_no_intent():
    """Test extraction of other not requested slots values
    from entities with the same names
    """

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"entities": [{"entity": "some_slot", "value": "some_value"}]},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    slot_values = form.extract_other_slots(
        CollectingDispatcher(), tracker, DEFAULT_DOMAIN
    )
    # check that the value was not extracted for requested slot
    assert slot_values == {}

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"entities": [{"entity": "some_other_slot", "value": "some_other_value"}]},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    slot_values = form.extract_other_slots(
        CollectingDispatcher(), tracker, DEFAULT_DOMAIN
    )
    # check that the value was extracted for non requested slot
    assert slot_values == {"some_other_slot": "some_other_value"}

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {
            "entities": [
                {"entity": "some_slot", "value": "some_value"},
                {"entity": "some_other_slot", "value": "some_other_value"},
            ]
        },
        [],
        False,
        None,
        {},
        "action_listen",
    )

    slot_values = form.extract_other_slots(
        CollectingDispatcher(), tracker, DEFAULT_DOMAIN
    )
    # check that the value was extracted only for non requested slot
    assert slot_values == {"some_other_slot": "some_other_value"}


def test_extract_other_slots_with_intent():
    """Test extraction of other not requested slots values
    from entities with the same names
    """

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {
            "intent": {"name": "some_other_intent", "confidence": 1.0},
            "entities": [{"entity": "some_other_slot", "value": "some_other_value"}],
        },
        [],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "some_slot": {
                "type": "any",
                "mappings": [
                    SlotMapping.from_entity(entity="some_slot", intent="some_intent")
                ],
            },
            "some_other_slot": {
                "type": "any",
                "mappings": [
                    SlotMapping.from_entity(
                        entity="some_other_slot", intent="some_intent"
                    )
                ],
            },
        }
    }

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, domain)
    # check that the value was extracted for non requested slot
    assert slot_values == {}

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {
            "intent": {"name": "some_intent", "confidence": 1.0},
            "entities": [{"entity": "some_other_slot", "value": "some_other_value"}],
        },
        [],
        False,
        None,
        {},
        "action_listen",
    )

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, domain)
    # check that the value was extracted only for non requested slot
    assert slot_values == {"some_other_slot": "some_other_value"}


@pytest.mark.parametrize(
    "some_other_slot_mapping, some_slot_mapping, entities, intent, expected_slot_values",
    [
        (
            [
                {
                    "type": "from_entity",
                    "intent": "some_intent",
                    "entity": "some_entity",
                    "role": "some_role",
                }
            ],
            [{"type": "from_entity", "intent": "some_intent", "entity": "some_entity"}],
            [
                {
                    "entity": "some_entity",
                    "value": "some_value",
                    "role": "some_other_role",
                }
            ],
            "some_intent",
            {},
        ),
        (
            [
                {
                    "type": "from_entity",
                    "intent": "some_intent",
                    "entity": "some_entity",
                    "role": "some_role",
                }
            ],
            [{"type": "from_entity", "intent": "some_intent", "entity": "some_entity"}],
            [{"entity": "some_entity", "value": "some_value", "role": "some_role"}],
            "some_intent",
            {"some_other_slot": "some_value"},
        ),
        (
            [
                {
                    "type": "from_entity",
                    "intent": "some_intent",
                    "entity": "some_entity",
                    "group": "some_group",
                }
            ],
            [{"type": "from_entity", "intent": "some_intent", "entity": "some_entity"}],
            [
                {
                    "entity": "some_entity",
                    "value": "some_value",
                    "group": "some_other_group",
                }
            ],
            "some_intent",
            {},
        ),
        (
            [
                {
                    "type": "from_entity",
                    "intent": "some_intent",
                    "entity": "some_entity",
                    "group": "some_group",
                }
            ],
            [{"type": "from_entity", "intent": "some_intent", "entity": "some_entity"}],
            [{"entity": "some_entity", "value": "some_value", "group": "some_group"}],
            "some_intent",
            {"some_other_slot": "some_value"},
        ),
        (
            [
                {
                    "type": "from_entity",
                    "intent": "some_intent",
                    "entity": "some_entity",
                    "group": "some_group",
                    "role": "some_role",
                }
            ],
            [{"type": "from_entity", "intent": "some_intent", "entity": "some_entity"}],
            [
                {
                    "entity": "some_entity",
                    "value": "some_value",
                    "role": "some_role",
                    "group": "some_group",
                }
            ],
            "some_intent",
            {"some_other_slot": "some_value"},
        ),
        (
            [{"type": "from_entity", "intent": "some_intent", "entity": "some_entity"}],
            [
                {
                    "type": "from_entity",
                    "intent": "some_intent",
                    "entity": "some_other_entity",
                }
            ],
            [{"entity": "some_entity", "value": "some_value"}],
            "some_intent",
            # other slot should be extracted because slot mapping is unique
            {"some_other_slot": "some_value"},
        ),
        (
            [
                {
                    "type": "from_entity",
                    "intent": "some_intent",
                    "entity": "some_entity",
                    "role": "some_role",
                }
            ],
            [
                {
                    "type": "from_entity",
                    "intent": "some_intent",
                    "entity": "some_other_entity",
                }
            ],
            [{"entity": "some_entity", "value": "some_value", "role": "some_role"}],
            "some_intent",
            # other slot should be extracted because slot mapping is unique
            {"some_other_slot": "some_value"},
        ),
        (
            [{"type": "from_entity", "intent": "some_intent", "entity": "some_entity"}],
            [
                {
                    "type": "from_entity",
                    "intent": "some_intent",
                    "entity": "some_other_entity",
                }
            ],
            [{"entity": "some_entity", "value": "some_value", "role": "some_role"}],
            "some_intent",
            # other slot should not be extracted
            # because even though slot mapping is unique it doesn't contain the role
            {},
        ),
        (
            [{"type": "from_entity", "intent": "some_intent", "entity": "some_entity"}],
            [{"type": "from_entity", "intent": "some_intent", "entity": "some_entity"}],
            [{"entity": "some_entity", "value": "some_value"}],
            "some_intent",
            # other slot should not be extracted because slot mapping is not unique
            {},
        ),
    ],
)
def test_extract_other_slots_with_entity(
    some_other_slot_mapping: List[Dict[Text, Any]],
    some_slot_mapping: List[Dict[Text, Any]],
    entities: List[Dict[Text, Any]],
    intent: Text,
    expected_slot_values: Dict[Text, Text],
):
    """Test extraction of other not requested slots values from entities."""

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"intent": {"name": intent, "confidence": 1.0}, "entities": entities},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "some_other_slot": {"type": "any", "mappings": some_other_slot_mapping},
            "some_slot": {"type": "any", "mappings": some_slot_mapping},
        },
    }

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, domain)
    # check that the value was extracted for non requested slot
    assert slot_values == expected_slot_values


async def test_validate():
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {
            "entities": [
                {"entity": "some_slot", "value": "some_value"},
                {"entity": "some_other_slot", "value": "some_other_value"},
            ]
        },
        [],
        False,
        None,
        {},
        "action_listen",
    )

    events = await form.validate(CollectingDispatcher(), tracker, DEFAULT_DOMAIN)
    # check that validation succeed
    assert events == [
        SlotSet("some_other_slot", "some_other_value"),
        SlotSet("some_slot", "some_value"),
    ] or events == [
        SlotSet("some_slot", "some_value"),
        SlotSet("some_other_slot", "some_other_value"),
    ]

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"entities": [{"entity": "some_other_slot", "value": "some_other_value"}]},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    events = await form.validate(CollectingDispatcher(), tracker, DEFAULT_DOMAIN)
    # check that validation succeed because other slot was extracted
    assert events == [SlotSet("some_other_slot", "some_other_value")]

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"entities": []},
        [],
        False,
        None,
        {},
        "action_listen",
    )
    with pytest.raises(Exception) as execinfo:
        await form.validate(CollectingDispatcher(), tracker, DEFAULT_DOMAIN)

    # check that validation failed gracefully
    assert execinfo.type == ActionExecutionRejection
    assert "Failed to extract slot some_slot with action some_form" in str(
        execinfo.value
    )


async def test_set_slot_within_helper():
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]

        def validate_some_slot(self, value, dispatcher, tracker, domain):
            if value == "some_value":
                return {
                    "some_slot": "validated_value",
                    "some_other_slot": "other_value",
                }

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {"entities": [{"entity": "some_slot", "value": "some_value"}]},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    events = await form.validate(CollectingDispatcher(), tracker, DEFAULT_DOMAIN)

    # check that some_slot gets validated correctly
    assert events == [
        SlotSet("some_other_slot", "other_value"),
        SlotSet("some_slot", "validated_value"),
    ] or events == [
        SlotSet("some_slot", "validated_value"),
        SlotSet("some_other_slot", "other_value"),
    ]


async def test_validate_extracted_no_requested():
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]

        def validate_some_slot(self, value, dispatcher, tracker, domain):
            if value == "some_value":
                return {"some_slot": "validated_value"}

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: None},
        {"entities": [{"entity": "some_slot", "value": "some_value"}]},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    events = await form.validate(CollectingDispatcher(), tracker, DEFAULT_DOMAIN)

    # check that some_slot gets validated correctly
    assert events == [SlotSet("some_slot", "validated_value")]


async def test_validate_prefilled_slots():
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]

        def validate_some_slot(self, value, dispatcher, tracker, domain):
            if value == "some_value":
                return {"some_slot": "validated_value"}
            else:
                return {"some_slot": None}

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {"some_slot": "some_value", "some_other_slot": "some_other_value"},
        {
            "entities": [{"entity": "some_slot", "value": "some_bad_value"}],
            "text": "some text",
        },
        [],
        False,
        None,
        {},
        "action_listen",
    )

    events = await form._activate_if_required(
        dispatcher=None, tracker=tracker, domain=DEFAULT_DOMAIN
    )
    # check that the form was activated and prefilled slots were validated
    assert events == [
        ActiveLoop("some_form"),
        SlotSet("some_slot", "validated_value"),
        SlotSet("some_other_slot", "some_other_value"),
    ]

    events.extend(
        await form._validate_if_required(
            dispatcher=None, tracker=tracker, domain=DEFAULT_DOMAIN
        )
    )

    # check that entities picked up in input overwrite prefilled slots
    assert events == [
        ActiveLoop("some_form"),
        SlotSet("some_slot", "validated_value"),
        SlotSet("some_other_slot", "some_other_value"),
        SlotSet("some_slot", None),
    ]


async def test_validate_trigger_slots():
    """Test validation results of from_trigger_intent slot mappings"""

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot"]

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {},
        {"intent": {"name": "trigger_intent", "confidence": 1.0}},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "some_slot": {
                "type": "any",
                "mappings": [SlotMapping.from_trigger_intent(value="some_value")],
            },
        },
    }

    slot_values = await form.validate(CollectingDispatcher(), tracker, domain)

    # check that the value was extracted on form activation
    assert slot_values == [
        {"event": "slot", "timestamp": None, "name": "some_slot", "value": "some_value"}
    ]

    tracker = Tracker(
        "default",
        {},
        {"intent": {"name": "trigger_intent", "confidence": 1.0}},
        [],
        False,
        None,
        {
            "name": "some_form",
            LOOP_INTERRUPTED_KEY: False,
            "rejected": False,
            "trigger_message": {
                "intent": {"name": "trigger_intent", "confidence": 1.0}
            },
        },
        "action_listen",
    )

    slot_values = await form.validate(CollectingDispatcher(), tracker, DEFAULT_DOMAIN)
    # check that the value was not extracted after form activation
    assert slot_values == []

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_other_slot"},
        {
            "intent": {"name": "some_other_intent", "confidence": 1.0},
            "entities": [{"entity": "some_other_slot", "value": "some_other_value"}],
        },
        [],
        False,
        None,
        {
            "name": "some_form",
            LOOP_INTERRUPTED_KEY: False,
            "rejected": False,
            "trigger_message": {
                "intent": {"name": "trigger_intent", "confidence": 1.0}
            },
        },
        "action_listen",
    )

    slot_values = await form.validate(CollectingDispatcher(), tracker, DEFAULT_DOMAIN)

    # check that validation failed gracefully
    assert slot_values == [
        {
            "event": "slot",
            "timestamp": None,
            "name": "some_other_slot",
            "value": "some_other_value",
        }
    ]


async def test_activate_if_required():
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {},
        {"intent": "some_intent", "entities": [], "text": "some text"},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    events = await form._activate_if_required(
        dispatcher=None, tracker=tracker, domain={}
    )
    # check that the form was activated
    assert events == [ActiveLoop("some_form")]

    tracker = Tracker(
        "default",
        {},
        {},
        [],
        False,
        None,
        {"name": "some_form", LOOP_INTERRUPTED_KEY: False, "rejected": False},
        "action_listen",
    )

    events = await form._activate_if_required(
        dispatcher=None, tracker=tracker, domain={}
    )
    # check that the form was not activated again
    assert events == []


async def test_validate_if_required():
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {
            "entities": [
                {"entity": "some_slot", "value": "some_value"},
                {"entity": "some_other_slot", "value": "some_other_value"},
            ]
        },
        [],
        False,
        None,
        {"name": "some_form", LOOP_INTERRUPTED_KEY: False, "rejected": False},
        "action_listen",
    )

    events = await form._validate_if_required(
        CollectingDispatcher(), tracker, DEFAULT_DOMAIN
    )
    # check that validation was performed
    assert events == [
        SlotSet("some_other_slot", "some_other_value"),
        SlotSet("some_slot", "some_value"),
    ] or events == [
        SlotSet("some_slot", "some_value"),
        SlotSet("some_other_slot", "some_other_value"),
    ]

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {
            "entities": [
                {"entity": "some_slot", "value": "some_value"},
                {"entity": "some_other_slot", "value": "some_other_value"},
            ]
        },
        [],
        False,
        None,
        {"name": "some_form", LOOP_INTERRUPTED_KEY: True, "rejected": False},
        "action_listen",
    )

    events = await form._validate_if_required(
        CollectingDispatcher(), tracker, DEFAULT_DOMAIN
    )
    # check that validation was skipped because loop was interrupted
    assert events == []

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_slot"},
        {
            "entities": [
                {"entity": "some_slot", "value": "some_value"},
                {"entity": "some_other_slot", "value": "some_other_value"},
            ]
        },
        [],
        False,
        None,
        {"name": "some_form", LOOP_INTERRUPTED_KEY: False, "rejected": False},
        "some_form",
    )

    events = await form._validate_if_required(
        CollectingDispatcher(), tracker, DEFAULT_DOMAIN
    )

    # check that validation was skipped
    # because previous action is not action_listen
    assert events == []


async def test_validate_on_activation():
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]

        async def submit(self, _dispatcher, _tracker, _domain):
            return []

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {},
        {"entities": [{"entity": "some_other_slot", "value": "some_other_value"}]},
        [],
        False,
        None,
        {},
        "action_listen",
    )
    dispatcher = CollectingDispatcher()
    events = await form.run(
        dispatcher=dispatcher, tracker=tracker, domain=DEFAULT_DOMAIN
    )
    # check that the form was activated and validation was performed
    assert events == [
        ActiveLoop("some_form"),
        SlotSet("some_other_slot", "some_other_value"),
        SlotSet(REQUESTED_SLOT, "some_slot"),
    ]


async def test_validate_on_activation_with_other_action_after_user_utterance():
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]

        async def submit(self, _dispatcher, _tracker, _domain):
            return []

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {},
        {"entities": [{"entity": "some_other_slot", "value": "some_other_value"}]},
        [],
        False,
        None,
        {},
        "some_action",
    )
    dispatcher = CollectingDispatcher()
    events = await form.run(
        dispatcher=dispatcher, tracker=tracker, domain=DEFAULT_DOMAIN
    )
    # check that the form was activated and validation was performed
    assert events == [
        ActiveLoop("some_form"),
        SlotSet("some_other_slot", "some_other_value"),
        SlotSet(REQUESTED_SLOT, "some_slot"),
    ]


class FormSyncValidate(FormAction):
    def name(self):
        return "some_form"

    @staticmethod
    def required_slots(_tracker):
        return ["some_slot", "some_other_slot"]

    def validate(self, dispatcher, tracker, domain):
        return self.deactivate()


class FormAsyncValidate(FormSyncValidate):
    async def validate(self, dispatcher, tracker, domain):
        # Not really necessary, just to emphasize this is async
        await asyncio.sleep(0)

        return self.deactivate()


@pytest.mark.parametrize("form_class", [FormSyncValidate, FormAsyncValidate])
async def test_early_deactivation(form_class: Type[FormAction]):
    # noinspection PyAbstractClass

    form = form_class()

    tracker = Tracker(
        "default",
        {"some_slot": "some_value"},
        {"intent": "greet"},
        [],
        False,
        None,
        {"name": "some_form", LOOP_INTERRUPTED_KEY: False, "rejected": False},
        "action_listen",
    )

    events = await form.run(dispatcher=None, tracker=tracker, domain={})

    # check that form was deactivated before requesting next slot
    assert events == [ActiveLoop(None), SlotSet(REQUESTED_SLOT, None)]
    assert SlotSet(REQUESTED_SLOT, "some_other_slot") not in events


class FormSyncSubmit(FormAction):
    def name(self):
        return "some_form"

    @staticmethod
    def required_slots(_tracker):
        return ["some_slot"]

    def submit(self, dispatcher, tracker, domain):
        return [SlotSet("other_slot", 42)]


class FormAsyncSubmit(FormSyncSubmit):
    async def submit(self, dispatcher, tracker, domain):
        # Not really necessary, just to emphasize this is async
        await asyncio.sleep(0)

        return [SlotSet("other_slot", 42)]


@pytest.mark.parametrize("form_class", [FormSyncSubmit, FormAsyncSubmit])
async def test_submit(form_class: Type[FormAction]):
    tracker = Tracker(
        "default",
        {"some_slot": "foobar", "other_slot": None},
        {"intent": "greet"},
        [],
        False,
        None,
        {"name": "some_form", LOOP_INTERRUPTED_KEY: True, "rejected": False},
        "action_listen",
    )

    form = form_class()
    events = await form.run(dispatcher=None, tracker=tracker, domain={})

    assert events[0]["value"] == 42


def test_form_deprecation():
    with pytest.warns(FutureWarning):
        FormAction()


class TestFormValidationAction(ValidationAction):
    def __init__(self, form_name: Text = "some_form") -> None:
        self.name_of_form = form_name

    def name(self) -> Text:
        return self.name_of_form

    def validate_slot1(
        self,
        slot_value: Any,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> Dict[Text, Any]:
        if slot_value == "correct_value":
            return {
                "slot1": "validated_value",
            }
        return {
            "slot1": None,
        }

    def validate_slot2(
        self,
        slot_value: Any,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> Dict[Text, Any]:
        if slot_value == "correct_value":
            return {
                "slot2": "validated_value",
            }
        return {
            "slot2": None,
        }

    async def validate_slot3(
        self,
        slot_value: Any,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> Dict[Text, Any]:
        if slot_value == "correct_value":
            return {
                "slot3": "validated_value",
            }
        # this function doesn't return anything when the slot value is incorrect


async def test_validation_action_outside_forms():
    class TestSlotValidationAction(ValidationAction):
        def global_slot_mappings(self) -> bool:
            return True

        def validate_slot2(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> Dict[Text, Any]:
            if slot_value == "Emily":
                return {
                    "slot2": "validated_value",
                }
            return {
                "slot2": None,
            }

    validation_action = TestSlotValidationAction()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [
            UserUttered(
                "My name is Emily.",
                parse_data={
                    "intent": {"name": "inform", "confidence": 1.0},
                    "entities": [{"entity": "name", "value": "Emily"}],
                },
            ),
            SlotSet("slot2", "Emily"),
        ],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "slot1": {
                "type": "any",
                "mappings": [SlotMapping.from_entity(entity="name", intent="test")],
            },
            "slot2": {
                "type": "any",
                "mappings": [SlotMapping.from_entity(entity="name", intent="inform")],
            },
        }
    }

    dispatcher = CollectingDispatcher()
    with pytest.warns(None) as warnings:
        events = await validation_action.run(
            dispatcher=dispatcher, tracker=tracker, domain=domain,
        )

    assert not warnings
    assert events == [
        SlotSet("slot2", "validated_value"),
    ]


async def test_validation_action_outside_forms_with_form_active_loop():
    class TestSlotValidationAction(ValidationAction):
        def global_slot_mappings(self) -> bool:
            return True

        def validate_slot1(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> Dict[Text, Any]:
            if slot_value == "Emily":
                return {
                    "slot1": "validated_value",
                }
            return {
                "slot1": None,
            }

    validation_action = TestSlotValidationAction()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [
            UserUttered(
                "My name is Emily.",
                parse_data={
                    "intent": {"name": "inform", "confidence": 1.0},
                    "entities": [{"entity": "name", "value": "Emily"}],
                },
            ),
            SlotSet("slot1", "Emily"),
        ],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "slot1": {
                "type": "any",
                "mappings": [
                    # this mapping means that the mapping should be validated by ValidationAction for `form1`
                    {
                        "type": "from_entity",
                        "entity": "name",
                        "conditions": [{"active_loop": "form1"}],
                    }
                ],
            },
        }
    }

    dispatcher = CollectingDispatcher()
    with pytest.warns(None) as warnings:
        events = await validation_action.run(
            dispatcher=dispatcher, tracker=tracker, domain=domain,
        )

    assert not warnings
    assert events == [
        SlotSet("slot1", "Emily"),
    ]


async def test_validation_action_for_form_outside_forms():
    class TestSlotValidationAction(ValidationAction):
        def name(self):
            return "validate_form1"

        def validate_slot1(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> Dict[Text, Any]:
            if slot_value == "Emily":
                return {
                    "slot1": "validated_value",
                }
            return {
                "slot1": None,
            }

    validation_action = TestSlotValidationAction()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [
            UserUttered(
                "My name is Emily.",
                parse_data={
                    "intent": {"name": "inform", "confidence": 1.0},
                    "entities": [{"entity": "name", "value": "Emily"}],
                },
            ),
            SlotSet("slot1", "Emily"),
        ],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "slot1": {
                "type": "any",
                "mappings": [SlotMapping.from_entity(entity="name", intent="inform")],
            },
        },
        "forms": {"form1": {"required_slots": []}},
    }

    dispatcher = CollectingDispatcher()
    with pytest.warns(None) as warnings:
        events = await validation_action.run(
            dispatcher=dispatcher, tracker=tracker, domain=domain,
        )

    assert not warnings
    assert events == [SlotSet("slot1", "Emily")]  # validation didn't run for this slot


async def test_form_validation_action():
    form_name = "test_form_validation_action"
    form = TestFormValidationAction(form_name)

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [SlotSet("slot1", "correct_value"), SlotSet("slot2", "incorrect_value")],
        False,
        None,
        {"name": form_name, "is_interrupted": False, "rejected": False},
        "action_listen",
    )

    domain = {
        "slots": {
            "slot1": {
                "type": "any",
                "mappings": [SlotMapping.from_entity(entity="slot1")],
            },
            "slot2": {
                "type": "any",
                "mappings": [SlotMapping.from_entity(entity="slot2")],
            },
        },
        "forms": {form_name: {"required_slots": ["slot1", "slot2"]}},
    }

    dispatcher = CollectingDispatcher()
    with pytest.warns(None) as warnings:
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=domain,)

    assert not warnings
    assert events == [
        SlotSet("slot1", "validated_value"),
        SlotSet("slot2", None),
    ]


async def test_form_validation_action_async():
    form_name = "some_form"
    form = TestFormValidationAction()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [SlotSet("slot3", "correct_value")],
        False,
        None,
        {"name": form_name, "is_interrupted": False, "rejected": False},
        "action_listen",
    )

    dispatcher = CollectingDispatcher()
    events = await form.run(
        dispatcher=dispatcher,
        tracker=tracker,
        domain={"forms": {form_name: {"required_slots": ["slot1", "slot3"]}}},
    )
    assert events == [SlotSet("slot3", "validated_value")]


async def test_form_validation_without_validate_function():
    form_name = "some_form"
    form = TestFormValidationAction()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [
            SlotSet("slot1", "correct_value"),
            SlotSet("slot2", "incorrect_value"),
            SlotSet("slot3", "some_value"),
        ],
        False,
        None,
        {"name": form_name, "is_interrupted": False, "rejected": False},
        "action_listen",
    )

    dispatcher = CollectingDispatcher()
    with pytest.warns(UserWarning):
        events = await form.run(
            dispatcher=dispatcher,
            tracker=tracker,
            domain={
                "forms": {form_name: {"required_slots": ["slot1", "slot2", "slot3"]}}
            },
        )

    assert events == [
        SlotSet("slot1", "validated_value"),
        SlotSet("slot2", None),
        SlotSet("slot3", "some_value"),
    ]


async def test_form_validation_changing_slots_during_validation():
    form_name = "some_form"

    class TestForm(ValidationAction):
        def name(self) -> Text:
            return form_name

        async def validate_my_slot(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> Dict[Text, Any]:
            return {"my_slot": None, "other_slot": "value"}

    form = TestForm()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [SlotSet("my_slot", "correct_value")],
        False,
        None,
        {"name": form_name, "is_interrupted": False, "rejected": False},
        "action_listen",
    )

    dispatcher = CollectingDispatcher()
    events = await form.run(
        dispatcher=dispatcher,
        tracker=tracker,
        domain={"forms": {form_name: {"required_slots": ["my_slot"]}}},
    )
    assert events == [
        SlotSet("my_slot", None),
        SlotSet("other_slot", "value"),
    ]


async def test_form_validation_dash_slot():
    form_name = "some_form"

    class TestFormValidationDashSlotAction(ValidationAction):
        def name(self) -> Text:
            return form_name

        def validate_slot_with_dash(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> Dict[Text, Any]:
            if slot_value == "correct_value":
                return {
                    "slot-with-dash": "validated_value",
                }
            return {
                "slot-with-dash": None,
            }

    form = TestFormValidationDashSlotAction()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [SlotSet("slot-with-dash", "correct_value")],
        False,
        None,
        {"name": form_name, "is_interrupted": False, "rejected": False},
        "action_listen",
    )

    dispatcher = CollectingDispatcher()
    events = await form.run(
        dispatcher=dispatcher,
        tracker=tracker,
        domain={"forms": {form_name: {"required_slots": ["slot-with-dash"]}}},
    )
    assert events == [
        SlotSet("slot-with-dash", "validated_value"),
    ]


@pytest.mark.parametrize(
    "required_slots, next_slot",
    [(["my_slot"], None), (["my_slot", "other_slot"], "other_slot")],
)
async def test_extract_and_validate_slot(
    required_slots: List[Text], next_slot: Optional[Text]
):
    custom_slot = "my_slot"
    unvalidated_value = "some value"
    validated_value = "validated value"

    class TestFormValidationWithCustomSlots(ValidationAction):
        def name(self) -> Text:
            return "some_form"

        async def required_slots(
            self,
            slots_mapped_in_domain: List[Text],
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> List[Text]:
            return required_slots

        async def extract_my_slot(
            self,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> Dict[Text, Any]:
            return {custom_slot: unvalidated_value}

        async def validate_my_slot(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> Dict[Text, Any]:
            assert slot_value == unvalidated_value
            return {custom_slot: validated_value}

    form = TestFormValidationWithCustomSlots()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [],
        False,
        None,
        {"name": "some_form", "is_interrupted": False, "rejected": False},
        "action_listen",
    )

    dispatcher = CollectingDispatcher()
    events = await form.run(dispatcher=dispatcher, tracker=tracker, domain={})

    assert events == [
        SlotSet(custom_slot, validated_value),
        SlotSet(REQUESTED_SLOT, next_slot),
    ]


@pytest.mark.parametrize(
    "my_required_slots, extracted_values, asserted_events",
    [
        (
            # request slot "state" before "city"
            ["state", "city"],
            # both are extracted as follow
            {"state": "california", "city": "san francisco"},
            # validate_state turns "california" to "CA"
            # validate_city sees "state" == "CA" and turns "san francisco" to "San Francisco"
            [["state", "CA"], ["city", "San Francisco"], [REQUESTED_SLOT, None]],
        ),
        (
            # request slot "city" before "state"
            ["city", "state"],
            # only "city" can be extracted from user message
            # seeing "city" == "san francisco", "state" is extracted as "california"
            {"state": None, "city": "san francisco"},
            # validate_city keeps "city" as is
            # validate_state turns "california" to "CA"
            [["city", "san francisco"], ["state", "CA"], [REQUESTED_SLOT, None]],
        ),
    ],
)
async def test_extract_and_validate_slot_visibility(
    my_required_slots: List[Text],
    extracted_values: Dict[Text, Any],
    asserted_events: List[List[Text]],
):
    class TestFormValidationWithCustomSlots(ValidationAction):
        def name(self) -> Text:
            return "some_form"

        async def required_slots(
            self,
            domain_slots: List[Tuple[Text, bool]],
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> List[Tuple[Text, bool]]:
            return my_required_slots

        async def extract_state(
            self,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> Dict[Text, Any]:
            state = extracted_values.get("state")
            if state is None and tracker.get_slot("city") == "san francisco":
                state = "california"
            return {"state": state}

        async def validate_state(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> Dict[Text, Any]:
            if slot_value == "california":
                slot_value = "CA"
            return {"state": slot_value}

        async def extract_city(
            self,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> Dict[Text, Any]:
            return {"city": extracted_values.get("city")}

        async def validate_city(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> Dict[Text, Any]:
            assert slot_value == "san francisco"
            if tracker.get_slot("state") == "CA":
                slot_value = "San Francisco"
            return {"city": slot_value}

    form = TestFormValidationWithCustomSlots()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [],
        False,
        None,
        {"name": "some_form", "is_interrupted": False, "rejected": False},
        "action_listen",
    )

    dispatcher = CollectingDispatcher()
    events = await form.run(dispatcher=dispatcher, tracker=tracker, domain={})

    assert events == [SlotSet(e[0], e[1]) for e in asserted_events]


async def test_extract_slot_only():
    custom_slot = "my_slot"
    unvalidated_value = "some value"

    class TestFormValidationWithCustomSlots(ValidationAction):
        def name(self) -> Text:
            return "some_form"

        async def required_slots(
            self,
            slots_mapped_in_domain: List[Text],
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> List[Text]:
            return [custom_slot]

        async def extract_my_slot(
            self,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> Dict[Text, Any]:
            return {custom_slot: unvalidated_value}

    form = TestFormValidationWithCustomSlots()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [],
        False,
        None,
        {"name": "some_form", "is_interrupted": False, "rejected": False},
        "action_listen",
    )

    dispatcher = CollectingDispatcher()
    events = await form.run(dispatcher=dispatcher, tracker=tracker, domain={})

    assert events == [
        SlotSet(custom_slot, unvalidated_value),
        SlotSet(REQUESTED_SLOT, None),
    ]


@pytest.mark.parametrize(
    "required_slots, domain, next_slot_events",
    [
        # Custom slot mapping but no `extract` method
        (["my_slot", "other_slot"], {}, [SlotSet(REQUESTED_SLOT, "other_slot")]),
        # Extract method for slot which is also mapped in domain
        (["my_slot"], {"forms": {"some_form": {"required_slots": ["my_slot"]}}}, [],),
    ],
)
async def test_warning_for_slot_extractions(
    required_slots: List[Text], domain: DomainDict, next_slot_events: List[EventType]
):
    custom_slot = "my_slot"
    unvalidated_value = "some value"

    class TestFormValidationWithCustomSlots(ValidationAction):
        def name(self) -> Text:
            return "some_form"

        async def required_slots(
            self,
            domain_slots: List[Text],
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> List[Text]:
            return required_slots

        async def extract_my_slot(
            self,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> Dict[Text, Any]:
            return {custom_slot: unvalidated_value}

    form = TestFormValidationWithCustomSlots()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [],
        False,
        None,
        {"name": "some_form", "is_interrupted": False, "rejected": False},
        "action_listen",
    )

    dispatcher = CollectingDispatcher()
    with pytest.warns(UserWarning):
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=domain)

    assert events == [SlotSet(custom_slot, unvalidated_value), *next_slot_events]


@pytest.mark.parametrize(
    "custom_slots, domain, expected_return_events",
    [
        # No domain slots, no custom slots
        ([], {}, [SlotSet(REQUESTED_SLOT, None)]),
        # Custom slot - no domain slots
        (["some value"], {}, [SlotSet(REQUESTED_SLOT, "some value")],),
        # Domain slots are ignored in overridden `required_slots`
        (
            [],
            {"forms": {"some_form": {"required_slots": ["another_slot"]}}},
            [SlotSet(REQUESTED_SLOT, None)],
        ),
        # `required_slots` was not overridden - Rasa Open Source will request next slot.
        # slot mappings with the `required_slots` keyword preceding them (new format)
        (
            ["another_slot"],
            {"forms": {"some_form": {"required_slots": ["another_slot"]}}},
            [],
        ),
    ],
)
async def test_ask_for_next_slot(
    custom_slots: List[Text], domain: Dict, expected_return_events: List[EventType],
):
    class TestFormRequestSlot(ValidationAction):
        def name(self) -> Text:
            return "some_form"

        async def required_slots(
            self,
            slots_mapped_in_domain: List[Tuple[Text, bool]],
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> List[Tuple[Text, bool]]:
            return custom_slots

    form = TestFormRequestSlot()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [],
        False,
        None,
        {"name": "some_form", "is_interrupted": False, "rejected": False},
        "action_listen",
    )

    dispatcher = CollectingDispatcher()
    events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=domain)
    assert events == expected_return_events
