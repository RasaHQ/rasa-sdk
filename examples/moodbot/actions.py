from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rasa_core_sdk import Action
from rasa_core_sdk.events import SlotSet


class MyCustomAction(Action):
    def name(self):
        return "my_custom_action"

    def run(self, dispatcher, tracker, domain):
        dispatcher.utter_template("utter_custom_template", tracker)
        return [SlotSet("test", 4)]
