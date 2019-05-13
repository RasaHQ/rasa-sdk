import pytest

from rasa_sdk.executor import ActionExecutor


@pytest.mark.parametrize(
    "noevent", [1, ["asd"], "asd", 3.2, None, {"event_without_event_property": 4}]
)
def test_event_validation_fails_on_odd_things(noevent):
    assert ActionExecutor.validate_events([noevent], "myaction") == []


def test_event_validation_accepts_dicts_with_event():
    assert ActionExecutor.validate_events([{"event": "user"}], "myaction") == [
        {"event": "user"}
    ]
