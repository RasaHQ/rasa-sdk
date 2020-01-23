import pytest
from datetime import datetime

import rasa_sdk.events as events


@pytest.mark.parametrize("intent", ["greet", "bye"])
def test_reminder_scheduled_correctly(intent):
    with pytest.warns(None):
        events.ReminderScheduled(intent, datetime.now())


@pytest.mark.parametrize("intent", ["action_something", "utter_greet"])
def test_reminder_scheduled_with_action(intent):
    with pytest.warns(FutureWarning):
        events.ReminderScheduled(intent, datetime.now())


@pytest.mark.parametrize("intent", ["greet", "bye"])
def test_reminder_cancelled_correctly(intent):
    with pytest.warns(None):
        events.ReminderCancelled(name="utter_something", intent_name=intent)


@pytest.mark.parametrize("intent", ["action_something", "utter_greet"])
def test_reminder_cancelled_with_action(intent):
    with pytest.warns(FutureWarning):
        events.ReminderCancelled(name="utter_something", intent_name=intent)
