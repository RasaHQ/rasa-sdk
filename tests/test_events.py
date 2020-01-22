import pytest

import warnings
from datetime import datetime

import rasa_sdk.events as events


def test_reminder_scheduled_correctly():
    with warnings.catch_warnings(record=True) as warning:
        events.ReminderScheduled("greet", datetime.now())
        assert len(warning) == 0


def test_reminder_scheduled_with_action():
    with warnings.catch_warnings(record=True) as warning:
        events.ReminderScheduled("action_greet", datetime.now())
        assert len(warning) == 1
        assert issubclass(warning[-1].category, FutureWarning)


def test_reminder_scheduled_with_utter_action():
    with warnings.catch_warnings(record=True) as warning:
        events.ReminderScheduled("utter_greet", datetime.now())
        assert len(warning) == 1
        assert issubclass(warning[-1].category, FutureWarning)


def test_reminder_cancelled_correctly():
    with warnings.catch_warnings(record=True) as warning:
        events.ReminderScheduled("greet", datetime.now())
        assert len(warning) == 0


def test_reminder_cancelled_with_action():
    with warnings.catch_warnings(record=True) as warning:
        events.ReminderScheduled("action_greet", datetime.now())
        assert len(warning) == 1
        assert issubclass(warning[-1].category, FutureWarning)


def test_reminder_cancelled_with_utter_action():
    with warnings.catch_warnings(record=True) as warning:
        events.ReminderScheduled("utter_greet", datetime.now())
        assert len(warning) == 1
        assert issubclass(warning[-1].category, FutureWarning)
