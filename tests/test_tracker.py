from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rasa_core_sdk import Tracker
from rasa_core_sdk.events import ActionExecuted, UserUttered


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
