import pytest
from datetime import datetime

import rasa_sdk.events as events


def test_reminder_scheduled_correctly():
    with pytest.warns(None):
        events.ReminderScheduled("greet", datetime.now())


def test_reminder_scheduled_with_action():
    with pytest.warns(FutureWarning):
        events.ReminderScheduled("action_greet", datetime.now())


def test_reminder_scheduled_with_utter_action():
    with pytest.warns(FutureWarning):
        events.ReminderScheduled("utter_greet", datetime.now())


def test_reminder_cancelled_correctly():
    with pytest.warns(None):
        events.ReminderScheduled("greet", datetime.now())


def test_reminder_cancelled_with_action():
    with pytest.warns(FutureWarning):
        events.ReminderScheduled("action_greet", datetime.now())


def test_reminder_cancelled_with_utter_action():
    with pytest.warns(FutureWarning):
        events.ReminderScheduled("utter_greet", datetime.now())
