import pytest

from rasa_sdk.interfaces import Tracker


def test_deprecation_warning_active_form():
    form = {"name": "my form"}
    state = {"events": [], "sender_id": "old", "active_loop": form}
    tracker = Tracker.from_dict(state)

    with pytest.warns(DeprecationWarning):
        assert tracker.active_form == form


def test_parsing_of_trackers_with_old_active_form_field():
    form = {"name": "my form"}
    state = {"events": [], "sender_id": "old", "active_form": form}
    tracker = Tracker.from_dict(state)

    assert tracker.active_loop == form
