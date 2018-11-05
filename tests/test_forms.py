from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import pytest
from rasa_core_sdk.forms import FormAction
from rasa_core_sdk import Tracker, ActionExecutionRejection
from rasa_core_sdk.executor import CollectingDispatcher
from rasa_core_sdk.events import SlotSet, Form


def test_extract_requested_slot_default():
    """Test default extraction of a slot value from entity with the same name
    """
    form = FormAction()

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'entities': [{'entity': 'some_slot',
                                     'value': 'some_value'}]},
                      [], False, None, {}, 'action_listen')

    slot_values = form.extract_requested_slot(CollectingDispatcher(),
                                              tracker, {})
    assert slot_values == {'some_slot': 'some_value'}


def test_extract_requested_slot_from_entity_no_intent():
    """Test extraction of a slot value from entity with the different name
        and any intent
    """
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def slot_mappings(self):
            return {"some_slot": self.from_entity(entity="some_entity")}
    form = CustomFormAction()

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'entities': [{'entity': 'some_entity',
                                     'value': 'some_value'}]},
                      [], False, None, {}, 'action_listen')

    slot_values = form.extract_requested_slot(CollectingDispatcher(),
                                              tracker, {})
    assert slot_values == {'some_slot': 'some_value'}


def test_extract_requested_slot_from_entity_with_intent():
    """Test extraction of a slot value from entity with the different name
        and certain intent
    """
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def slot_mappings(self):
            return {"some_slot": self.from_entity(entity="some_entity",
                                                  intent="some_intent")}
    form = CustomFormAction()

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'intent': {'name': 'some_intent', 'confidence': 1.0},
                       'entities': [{'entity': 'some_entity',
                                     'value': 'some_value'}]},
                      [], False, None, {}, 'action_listen')

    slot_values = form.extract_requested_slot(CollectingDispatcher(),
                                              tracker, {})
    # check that the value was extracted for correct intent
    assert slot_values == {'some_slot': 'some_value'}

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'intent': {'name': 'some_other_intent',
                                  'confidence': 1.0},
                       'entities': [{'entity': 'some_entity',
                                     'value': 'some_value'}]},
                      [], False, None, {}, 'action_listen')

    slot_values = form.extract_requested_slot(CollectingDispatcher(),
                                              tracker, {})
    # check that the value was not extracted for incorrect intent
    assert slot_values == {}


def test_extract_requested_slot_from_intent():
    """Test extraction of a slot value from certain intent
    """
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def slot_mappings(self):
            return {"some_slot": self.from_intent(intent="some_intent",
                                                  value="some_value")}
    form = CustomFormAction()

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'intent': {'name': 'some_intent',
                                  'confidence': 1.0}},
                      [], False, None, {}, 'action_listen')

    slot_values = form.extract_requested_slot(CollectingDispatcher(),
                                              tracker, {})
    # check that the value was extracted for correct intent
    assert slot_values == {'some_slot': 'some_value'}

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'intent': {'name': 'some_other_intent',
                                  'confidence': 1.0}},
                      [], False, None, {}, 'action_listen')

    slot_values = form.extract_requested_slot(CollectingDispatcher(),
                                              tracker, {})
    # check that the value was not extracted for incorrect intent
    assert slot_values == {}


def test_extract_requested_slot_from_text_no_intent():
    """Test extraction of a slot value from text with any intent
    """
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def slot_mappings(self):
            return {"some_slot": self.from_text()}
    form = CustomFormAction()

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'text': 'some_text'},
                      [], False, None, {}, 'action_listen')

    slot_values = form.extract_requested_slot(CollectingDispatcher(),
                                              tracker, {})
    assert slot_values == {'some_slot': 'some_text'}


def test_extract_requested_slot_from_text_with_intent():
    """Test extraction of a slot value from text with certain intent
    """
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def slot_mappings(self):
            return {"some_slot": self.from_text(intent='some_intent')}
    form = CustomFormAction()

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'text': 'some_text',
                       'intent': {'name': 'some_intent',
                                  'confidence': 1.0}},
                      [], False, None, {}, 'action_listen')

    slot_values = form.extract_requested_slot(CollectingDispatcher(),
                                              tracker, {})
    # check that the value was extracted for correct intent
    assert slot_values == {'some_slot': 'some_text'}

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'text': 'some_text',
                       'intent': {'name': 'some_other_intent',
                                  'confidence': 1.0}},
                      [], False, None, {}, 'action_listen')

    slot_values = form.extract_requested_slot(CollectingDispatcher(),
                                              tracker, {})
    # check that the value was not extracted for incorrect intent
    assert slot_values == {}


def test_extract_other_slots():
    """Test extraction of other not requested slots values
        from entities with the same names
    """
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]
    form = CustomFormAction()

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'entities': [{'entity': 'some_slot',
                                     'value': 'some_value'}]},
                      [], False, None, {}, 'action_listen')

    slot_values = form.extract_other_slots(CollectingDispatcher(),
                                           tracker, {})
    # check that the value was not extracted for requested slot
    assert slot_values == {}

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'entities': [{'entity': 'some_other_slot',
                                     'value': 'some_other_value'}]},
                      [], False, None, {}, 'action_listen')

    slot_values = form.extract_other_slots(CollectingDispatcher(),
                                           tracker, {})
    # check that the value was extracted for non requested slot
    assert slot_values == {'some_other_slot': 'some_other_value'}

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'entities': [{'entity': 'some_slot',
                                     'value': 'some_value'},
                                    {'entity': 'some_other_slot',
                                     'value': 'some_other_value'}]},
                      [], False, None, {}, 'action_listen')

    slot_values = form.extract_other_slots(CollectingDispatcher(),
                                           tracker, {})
    # check that the value was extracted only for non requested slot
    assert slot_values == {'some_other_slot': 'some_other_value'}


def test_validate():
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]
    form = CustomFormAction()

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'entities': [{'entity': 'some_slot',
                                     'value': 'some_value'},
                                    {'entity': 'some_other_slot',
                                     'value': 'some_other_value'}]},
                      [], False, None, {}, 'action_listen')

    events = form.validate(CollectingDispatcher(), tracker, {})
    # check that validation succeed
    assert events == [SlotSet('some_other_slot', 'some_other_value'),
                      SlotSet('some_slot', 'some_value')]

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'entities': [{'entity': 'some_other_slot',
                                     'value': 'some_other_value'}]},
                      [], False, None, {}, 'action_listen')

    events = form.validate(CollectingDispatcher(), tracker, {})
    # check that validation succeed because other slot was extracted
    assert events == [SlotSet('some_other_slot', 'some_other_value')]

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'entities': []},
                      [], False, None, {}, 'action_listen')
    with pytest.raises(Exception) as execinfo:
        form.validate(CollectingDispatcher(), tracker, {})

    # check that validation failed gracefully
    assert execinfo.type == ActionExecutionRejection
    assert ("Failed to validate slot some_slot "
            "with action some_form" in str(execinfo.value))


def test_activate_if_required():
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"
    form = CustomFormAction()

    tracker = Tracker('default', {}, {},
                      [], False, None, {}, 'action_listen')

    events = form._activate_if_required(tracker)
    # check that the form was activated
    assert events == [Form('some_form')]

    tracker = Tracker('default', {}, {}, [], False, None,
                      {'name': 'some_form',
                       'validate': True, 'rejected': False},
                      'action_listen')

    events = form._activate_if_required(tracker)
    # check that the form was not activated again
    assert events == []


def test_validate_if_required():
    # noinspection PyAbstractClass
    class CustomFormAction(FormAction):
        def name(self):
            return "some_form"

        @staticmethod
        def required_slots(_tracker):
            return ["some_slot", "some_other_slot"]
    form = CustomFormAction()

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'entities': [{'entity': 'some_slot',
                                     'value': 'some_value'},
                                    {'entity': 'some_other_slot',
                                     'value': 'some_other_value'}]},
                      [], False, None,
                      {'name': 'some_form',
                       'validate': True, 'rejected': False},
                      'action_listen')

    events = form._validate_if_required(CollectingDispatcher(), tracker, {})
    # check that validation was performed
    assert events == [SlotSet('some_other_slot', 'some_other_value'),
                      SlotSet('some_slot', 'some_value')]

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'entities': [{'entity': 'some_slot',
                                     'value': 'some_value'},
                                    {'entity': 'some_other_slot',
                                     'value': 'some_other_value'}]},
                      [], False, None,
                      {'name': 'some_form',
                       'validate': False, 'rejected': False},
                      'action_listen')

    events = form._validate_if_required(CollectingDispatcher(), tracker, {})
    # check that validation was skipped because 'validate': False
    assert events == []

    tracker = Tracker('default', {'requested_slot': 'some_slot'},
                      {'entities': [{'entity': 'some_slot',
                                     'value': 'some_value'},
                                    {'entity': 'some_other_slot',
                                     'value': 'some_other_value'}]},
                      [], False, None,
                      {'name': 'some_form',
                       'validate': True, 'rejected': False},
                      'some_form')

    events = form._validate_if_required(CollectingDispatcher(), tracker, {})
    # check that validation was skipped
    # because previous action is not action_listen
    assert events == []
