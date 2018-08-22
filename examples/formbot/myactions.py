from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rasa_core_sdk import Action
from rasa_core_sdk.events import SlotSet, StartForm, EndForm
from rasa_core_sdk.forms import SimpleForm


class StartFormAction(Action):
    def name(self):
        return "start_restaurant"

    def run(self, dispatcher, tracker, domain, executor):
        return [StartForm("restaurant_form")]


class EndFormAction(Action):
    def name(self):
        return "end_form"

    def run(self, dispatcher, tracker, domain, executor):
        form = executor.forms[tracker.active_form]
        still_to_go = form.check_unfilled_slots(tracker)
        complete = len(still_to_go) == 0
        return [SlotSet('form_complete', complete), EndForm()]


class VegetarianParse(Action):
    def name(self):
        return "vegetarian_parse"

    def run(self, dispatcher, tracker, domain, executor):
        latest_intent = tracker.latest_message['intent']['name']
        if latest_intent == 'affirm':
            return [SlotSet('vegetarian', True)]
        elif latest_intent == 'deny':
            return [SlotSet('vegetarian', False)]
        else:
            return []


class RestaurantForm(SimpleForm):
    def __init__(self):
        name = 'restaurant_form'
        fields = {
            "price": {
                "ask_utt": "utter_ask_price",
                "clarify_utt": "utter_explain_price",
                "priority": 0
            },
            "cuisine": {
                "ask_utt": "utter_ask_cuisine",
                "clarify_utt": "utter_explain_cuisine",

            },
            "people": {
                "ask_utt": "utter_ask_people",
                "clarify_utt": "utter_explain_people"
            },
            "location": {
                "ask_utt": "utter_ask_location",
                "clarify_utt": "utter_explain_location"
            },
            "vegetarian": {
                "ask_utt": "utter_ask_vegetarian",
                "clarify_utt": "utter_explain_vegetarian",
                "follow_up_action": "vegetarian_parse",
                'priority': 0
            }
        }

        finish_action = "end_form"

        breakout_intents = {
            "goodbye": "end_form",
            "request_hotel": "end_form"
        }

        chitchat_intents = {"chitchat": "utter_chitchat"}

        details_intent = "ask_details"

        rules = {
            "cuisine": {
                "mcdonalds": {
                              'need': ['location'],
                              'lose': ['people', 'price']
                              }
            }
        }

        failure_action = 'utter_human_hand_off'
        super(RestaurantForm, self).__init__(name, fields, finish_action, breakout_intents, chitchat_intents, details_intent,
                                             rules, failure_action=failure_action)