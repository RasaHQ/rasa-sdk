from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rasa_core_sdk import Action, Tracker
from rasa_core_sdk.events import SlotSet
from rasa_core_sdk.executor import ActionExecutor, CollectingDispatcher


class CustomActionBase(Action):
    @classmethod
    def name(cls):
        # Name method needed to test if base action was registered
        return "base_action"

    class Meta:
        abstract = True

    @staticmethod
    def some_common_feature():
        return "test"

    def run(self, dispatcher, tracker, domain):
        raise NotImplementedError


class CustomAction(CustomActionBase):

    @classmethod
    def name(cls):
        return "custom_action"

    def run(self, dispatcher, tracker, domain):
        return [SlotSet('test', self.some_common_feature())]


def test_abstract_action():
    executor = ActionExecutor()
    executor.register_package('tests')
    assert CustomAction.name() in executor.actions
    assert CustomActionBase.name() not in executor.actions

    dispatcher = CollectingDispatcher()
    tracker = Tracker('test', {}, {}, [], False, None, {}, 'listen')
    domain = {}

    events = CustomAction().run(dispatcher, tracker, domain)
    assert events == [SlotSet('test', "test")]
