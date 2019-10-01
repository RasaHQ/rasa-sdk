from rasa_sdk import Tracker
from rasa_sdk.events import ActionExecuted, UserUttered


def test_latest_input_channel():
    tracker = Tracker(
        "default",
        {},
        {"intent": {"name": "some_intent", "confidence": 1.0}},
        [
            UserUttered("my message text", input_channel="superchat"),
            ActionExecuted("action_listen"),
        ],
        False,
        None,
        {},
        "action_listen",
    )

    assert tracker.get_latest_input_channel() == "superchat"
