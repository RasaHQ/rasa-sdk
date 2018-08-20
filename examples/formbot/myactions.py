from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rasa_core_sdk import Action
from rasa_core_sdk.events import SlotSet, StartForm, EndForm
from rasa_core_sdk.forms import SimpleForm

class MyCustomAction(Action):
    def name(self):
        return "my_custom_action"

    def run(self, dispatcher, tracker, domain, executor):
        dispatcher.utter_template("utter_custom_template", tracker)
        return [SlotSet("test", 4)]


class StartFormAction(Action):
    def name(self):
        return "start_restaurant"

    def run(self, dispatcher, tracker, domain, executor):
        return [StartForm("restaurant_form")]


class EndFormAction(Action):
    def name(self):
        return "end_form"

    def run(self, dispatcher, tracker, domain, executor):
        #request_hotel, goodbye, finished, etc.
        return [EndForm()]


class RestaurantForm(SimpleForm):
    def __init__(self):
        name = 'restaurant_form'
        slot_dict = {
            "price": {
                "ask_utt": "utter_ask_price",
                "clarify_utt": "utter_explain_price_restaurant",
                "priority": 0
            },
            "cuisine": {
                "ask_utt": "utter_ask_cuisine",
                "clarify_utt": "utter_explain_cuisine_restaurant"
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
        super(RestaurantForm, self).__init__(name, slot_dict, finish_action, exit_dict, chitchat_dict, details_intent,
                                             rules, failure_action=failure_action)