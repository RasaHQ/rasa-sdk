import pytest
import asyncio
from typing import Type, Text, Dict, Any, List, Optional

from rasa_sdk import Tracker, ActionExecutionRejection
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet, ActiveLoop
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormAction, FormSlotsValidatorAction, REQUESTED_SLOT, LOOP_INTERRUPTED_KEY


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

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", {}
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

        def slot_mappings(self):
            return {"some_slot": self.from_entity(entity="some_entity")}

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

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", {}
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

        def slot_mappings(self):
            return {
                "some_slot": self.from_entity(
                    entity="some_entity", intent="some_intent"
                )
            }

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

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", {}
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
        CollectingDispatcher(), tracker, "some_slot", {}
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
            {"some_slot": "some_value"},
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

        def slot_mappings(self):
            return {
                "some_slot": self.from_entity(
                    entity="some_entity",
                    role=mapping_role,
                    group=mapping_group,
                    intent=mapping_intent,
                    not_intent=mapping_not_intent,
                )
            }

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

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", {}
    )
    assert slot_values == expected_slot_values


def test_extract_requested_slot_from_intent():
    """Test extraction of a slot value from certain intent"""

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        def slot_mappings(self):
            return {
                "some_slot": self.from_intent(intent="some_intent", value="some_value")
            }

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

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", {}
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
        CollectingDispatcher(), tracker, "some_slot", {}
    )
    # check that the value was not extracted for incorrect intent
    assert slot_values == {}


def test_extract_requested_slot_from_not_intent():
    """Test extraction of a slot value from certain intent"""

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        def slot_mappings(self):
            return {
                "some_slot": self.from_intent(
                    not_intent="some_intent", value="some_value"
                )
            }

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

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", {}
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
        CollectingDispatcher(), tracker, "some_slot", {}
    )
    # check that the value was not extracted for incorrect intent
    assert slot_values == {"some_slot": "some_value"}


def test_extract_requested_slot_from_text_no_intent():
    """Test extraction of a slot value from text with any intent"""

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        def slot_mappings(self):
            return {"some_slot": self.from_text()}

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

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", {}
    )
    assert slot_values == {"some_slot": "some_text"}


def test_extract_requested_slot_from_text_with_intent():
    """Test extraction of a slot value from text with certain intent"""

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        def slot_mappings(self):
            return {"some_slot": self.from_text(intent="some_intent")}

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

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", {}
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
        CollectingDispatcher(), tracker, "some_slot", {}
    )
    # check that the value was not extracted for incorrect intent
    assert slot_values == {}


def test_extract_requested_slot_from_text_with_not_intent():
    """Test extraction of a slot value from text with certain intent"""

    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        def slot_mappings(self):
            return {"some_slot": self.from_text(not_intent="some_intent")}

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

    slot_values = form.extract_requested_slot(
        CollectingDispatcher(), tracker, "some_slot", {}
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
        CollectingDispatcher(), tracker, "some_slot", {}
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

        def slot_mappings(self):
            return {
                "some_slot": self.from_trigger_intent(
                    intent="trigger_intent", value="some_value"
                )
            }

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

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, {})
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

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, {})
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

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, {})
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

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, {})
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

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, {})
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

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, {})

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

        def slot_mappings(self):
            return {
                "some_other_slot": self.from_entity(
                    entity="some_other_slot", intent="some_intent"
                )
            }

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

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, {})
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

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, {})
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
            [
                {
                    "type": "from_entity",
                    "intent": "some_intent",
                    "entity": "some_other_entity",
                }
            ],
            [{"entity": "some_entity", "value": "some_value", "role": "some_role"}],
            "some_intent",
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

        def slot_mappings(self):
            return {
                "some_other_slot": some_other_slot_mapping,
                "some_slot": some_slot_mapping,
            }

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

    slot_values = form.extract_other_slots(CollectingDispatcher(), tracker, {})
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

    events = await form.validate(CollectingDispatcher(), tracker, {})
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

    events = await form.validate(CollectingDispatcher(), tracker, {})
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
        await form.validate(CollectingDispatcher(), tracker, {})

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

    events = await form.validate(CollectingDispatcher(), tracker, {})

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

    events = await form.validate(CollectingDispatcher(), tracker, {})

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
        dispatcher=None, tracker=tracker, domain=None
    )
    # check that the form was activated and prefilled slots were validated
    assert events == [
        ActiveLoop("some_form"),
        SlotSet("some_slot", "validated_value"),
        SlotSet("some_other_slot", "some_other_value"),
    ]

    events.extend(
        await form._validate_if_required(dispatcher=None, tracker=tracker, domain=None)
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

        def slot_mappings(self):
            return {
                "some_slot": self.from_trigger_intent(
                    intent="trigger_intent", value="some_value"
                )
            }

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

    slot_values = await form.validate(CollectingDispatcher(), tracker, {})

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

    slot_values = await form.validate(CollectingDispatcher(), tracker, {})
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

    slot_values = await form.validate(CollectingDispatcher(), tracker, {})

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
        dispatcher=None, tracker=tracker, domain=None
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
        dispatcher=None, tracker=tracker, domain=None
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

    events = await form._validate_if_required(CollectingDispatcher(), tracker, {})
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

    events = await form._validate_if_required(CollectingDispatcher(), tracker, {})
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

    events = await form._validate_if_required(CollectingDispatcher(), tracker, {})

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
    events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
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
    events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
    # check that the form was activated and validation was performed
    assert events == [
        ActiveLoop("some_form"),
        SlotSet("some_other_slot", "some_other_value"),
        SlotSet(REQUESTED_SLOT, "some_slot"),
    ]


async def test_deprecated_helper_style():
    # noinspection PyAbstractClass
    # This method tests the old style of returning values instead of {'slot':'value'}
    # dicts, and can be removed if we officially stop supporting the deprecated style.
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]

        def validate_some_slot(self, value, dispatcher, tracker, domain):
            if value == "some_value":
                return "validated_value"

    form = CustomFormAction()

    tracker = Tracker(
        "default",
        {REQUESTED_SLOT: "some_value"},
        {"entities": [{"entity": "some_slot", "value": "some_value"}]},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    events = await form.validate(CollectingDispatcher(), tracker, {})

    # check that some_slot gets validated correctly
    assert events == [SlotSet("some_slot", "validated_value")]


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

    events = await form.run(dispatcher=None, tracker=tracker, domain=None)

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
    events = await form.run(dispatcher=None, tracker=tracker, domain=None)

    assert events[0]["value"] == 42


def test_form_deprecation():
    with pytest.warns(FutureWarning):
        FormAction()


class TestFormSlotValidator(FormSlotsValidatorAction):
    def name(self) -> Text:
        return "some_form"

    @staticmethod
    def validate_slot1(tracker: Tracker, domain: "DomainDict", slot_value: Any) -> bool:
        return slot_value == "correct_value"

    @staticmethod
    def validate_slot2(tracker: Tracker, domain: "DomainDict", slot_value: Any) -> bool:
        return slot_value == "correct_value"


async def test_form_slot_validator():
    form = TestFormSlotValidator()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [SlotSet("slot1", "correct_value"), SlotSet("slot2", "incorrect_value")],
        False,
        None,
        {"name": "some_form", "validate": True, "rejected": False},
        "action_listen",
    )

    dispatcher = CollectingDispatcher()
    events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
    # check that the form was activated and validation was performed
    assert events == [
        SlotSet("slot2", None),
        SlotSet("slot1", "correct_value"),
    ]


async def test_form_slot_validator_attribute_error():
    form = TestFormSlotValidator()

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
        {"name": "some_form", "validate": True, "rejected": False},
        "action_listen",
    )

    dispatcher = CollectingDispatcher()
    with pytest.raises(AttributeError):
        await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
