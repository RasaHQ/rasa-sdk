import pytest
from datetime import datetime

import rasa_sdk.events as events


def test_reminder_scheduled_correctly():
    with pytest.warns(None):
        events.ReminderScheduled("greet", datetime.now())


@pytest.mark.parametrize("intent", ["action_something", "utter_greet"])
def test_reminder_scheduled_with_action(intent):
    with pytest.warns(FutureWarning):
        events.ReminderScheduled(intent, datetime.now())


def test_reminder_cancelled_correctly():
    with pytest.warns(None):
        events.ReminderScheduled("greet", datetime.now())


@pytest.mark.parametrize("intent", ["action_something", "utter_greet"])
def test_reminder_cancelled_with_action(intent):
    with pytest.warns(FutureWarning):
        events.ReminderScheduled("action_greet", datetime.now())
