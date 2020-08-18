import pytest

from rasa_sdk.interfaces import Tracker


def test_deprecation_warning_active_form():
    form = {"name": "my form"}
    state = {"events": [], "sender_id": "old", "active_loop": form}
    tracker = Tracker.from_dict(state)

    with pytest.warns(DeprecationWarning):
        assert tracker.active_form == form
