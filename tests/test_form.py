from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rasa_core_sdk.forms import SimpleForm
from rasa_core_sdk import Tracker
from rasa_core.channels.channel import UserMessage
import logging


logger = logging.getLogger(__name__)


class TestForm(SimpleForm):
    def __init__(self):
        name = 'test_form'
        slot_dict = {
            "price": {
                "ask_utt": "utter_ask_price",
                "clarify_utt": "utter_explain_price_restaurant",
                "priority": 0
            },
            "cuisine": {
                "ask_utt": "utter_ask_cuisine",
                "clarify_utt": "utter_explain_cuisine_restaurant",
                "priority": 1
            },
            "people": {
                "ask_utt": "utter_ask_people",
                "clarify_utt": "utter_explain_people_restaurant"
            },
            "location": {
                "ask_utt": "utter_ask_location",
                "clarify_utt": "utter_explain_location_restaurant"
            }
        }

        finish_action = "end_form"

        exit_dict = {
            "goodbye": "end_form",
            "request_hotel": "end_form"
        }

        chitchat_dict = {"chitchat": "utter_chitchat"}

        details_intent = "utter_ask_details"

        rules = {
            "cuisine": {
                "mcdonalds": {
                              'need': ['location'],
                              'lose': ['people', 'price']
                              }
            }
        }

        failure_action = 'utter_human_hand_off'
        super(TestForm, self).__init__(name, slot_dict,
                                       finish_action, exit_dict,
                                       chitchat_dict, details_intent,
                                       rules, failure_action=failure_action)


def test_endpoint():
    pass


def test_next_action():
    slots = {'price': None, "cuisine": None,
             "people": None, "location": None}
    latest_message = {"intent": {"name": "greet"}}
    tracker = Tracker(UserMessage.DEFAULT_SENDER_ID, slots, latest_message,
                      [], False, None)
    form = TestForm()
    assert form.next_action(tracker) == 'utter_ask_price'
    assert form.next_action(tracker) == 'action_listen'

    slots['price'] = 'high'
    tracker = Tracker(UserMessage.DEFAULT_SENDER_ID, slots, latest_message,
                      [], False, None)
    assert form.next_action(tracker) == 'utter_ask_cuisine'
    assert form.next_action(tracker) == 'action_listen'

    latest_message = {"intent": {"name": "utter_ask_details"}}
    tracker = Tracker(UserMessage.DEFAULT_SENDER_ID, slots, latest_message,
                      [], False, None)
    assert form.next_action(tracker) == 'utter_explain_cuisine_restaurant'
    assert form.next_action(tracker) == 'utter_ask_cuisine'
    assert form.next_action(tracker) == 'action_listen'
    latest_message = {"intent": {"name": "chitchat"}}
    tracker = Tracker(UserMessage.DEFAULT_SENDER_ID, slots, latest_message,
                      [], False, None)

    assert form.next_action(tracker) == 'utter_chitchat'
    assert form.next_action(tracker) == 'utter_ask_cuisine'
    assert form.next_action(tracker) == 'action_listen'

    slots = {'price': 'price', "cuisine": 'cuisine',
             "people": 'ppl', "location": 'loc'}

    tracker = Tracker(UserMessage.DEFAULT_SENDER_ID, slots, latest_message,
                      [], False, None)
    form.next_action(tracker)
    assert form.next_action(tracker) == 'end_form'
