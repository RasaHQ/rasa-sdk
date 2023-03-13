import pytest
from typing import Text, Dict, Any, List, Optional

from rasa_sdk import Tracker
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet, EventType, UserUttered
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import (
    ValidationAction,
    FormValidationAction,
    REQUESTED_SLOT,
)
from rasa_sdk.slots import SlotMapping

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


class TestFormValidationAction(FormValidationAction):
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
            dispatcher=dispatcher,
            tracker=tracker,
            domain=domain,
        )

    assert not warnings
    assert events == [
        SlotSet("slot2", "validated_value"),
    ]


async def test_validation_action_outside_forms_with_form_active_loop():
    class TestSlotValidationAction(ValidationAction):
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
            dispatcher=dispatcher,
            tracker=tracker,
            domain=domain,
        )

    assert not warnings
    assert events == []  # validation didn't run for this slot


async def test_form_validation_action_doesnt_work_for_global_slots():
    class TestSlotValidationAction(FormValidationAction):
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
            dispatcher=dispatcher,
            tracker=tracker,
            domain=domain,
        )

    assert not warnings
    # validation shoudn't run because `TestSlotValidationAction` implements
    # `FormValidationAction` and `slot1` is not assigned to any form
    assert events == []


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
        events = await form.run(
            dispatcher=dispatcher,
            tracker=tracker,
            domain=domain,
        )

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

    class TestForm(FormValidationAction):
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

    class TestFormValidationDashSlotAction(FormValidationAction):
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

    class TestFormValidationWithCustomSlots(FormValidationAction):
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


async def test_extract_and_validate_global_slot():
    custom_slot = "my_slot"
    unvalidated_value = "some value"
    validated_value = "validated value"

    class TestFormValidationWithCustomSlots(ValidationAction):
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

    validation_action = TestFormValidationWithCustomSlots()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [],
        False,
        None,
        {},
        "action_listen",
    )

    domain = {
        "slots": {
            "my_slot": {
                "type": "any",
                "mappings": [SlotMapping.from_entity(entity="my_slot")],
            },
            "other_slot": {
                "type": "any",
                "mappings": [SlotMapping.from_entity(entity="other_slot")],
            },
        },
    }

    dispatcher = CollectingDispatcher()
    events = await validation_action.run(
        dispatcher=dispatcher, tracker=tracker, domain=domain
    )

    assert events == [SlotSet(custom_slot, validated_value)]


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
    class TestFormValidationWithCustomSlots(FormValidationAction):
        def name(self) -> Text:
            return "some_form"

        async def required_slots(
            self,
            domain_slots: List[Text],
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> List[Text]:
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

    class TestFormValidationWithCustomSlots(FormValidationAction):
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
        (
            ["my_slot", "other_slot"],
            {"forms": {"some_form": {"required_slots": ["my_slot"]}}},
            [SlotSet(REQUESTED_SLOT, "other_slot")],
        ),
    ],
)
async def test_warning_for_slot_extractions(
    required_slots: List[Text], domain: DomainDict, next_slot_events: List[EventType]
):
    custom_slot = "my_slot"
    unvalidated_value = "some value"

    class TestFormValidationWithCustomSlots(FormValidationAction):
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
        ([], {}, []),
        # Custom slot - no domain slots
        (
            ["some value"],
            {},
            [SlotSet(REQUESTED_SLOT, "some value")],
        ),
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
    custom_slots: List[Text],
    domain: Dict,
    expected_return_events: List[EventType],
):
    class TestFormRequestSlot(FormValidationAction):
        def name(self) -> Text:
            return "some_form"

        async def required_slots(
            self,
            domain_slots: List[Text],
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> List[Text]:
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


async def test_form_validation_space_slot():
    form_name = "some_form"

    class TestFormValidationSpaceSlotAction(FormValidationAction):
        def name(self) -> Text:
            return form_name

        def validate_space_slot(
            self,
            slot_value: Any,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
        ) -> Dict[Text, Any]:
            if slot_value == "correct_value":
                return {
                    "space.slot": "validated_value",
                }
            return {
                "space.slot": None,
            }

    form = TestFormValidationSpaceSlotAction()

    # tracker with active form
    tracker = Tracker(
        "default",
        {},
        {},
        [SlotSet("space.slot", "correct_value")],
        False,
        None,
        {"name": form_name, "is_interrupted": False, "rejected": False},
        "action_listen",
    )

    dispatcher = CollectingDispatcher()
    events = await form.run(
        dispatcher=dispatcher,
        tracker=tracker,
        domain={"forms": {form_name: {"required_slots": ["space.slot"]}}},
    )
    assert events == [
        SlotSet("space.slot", "validated_value"),
    ]
