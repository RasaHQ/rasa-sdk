from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rasa_core_sdk import Action
from rasa_core_sdk.executor import ActionExecutor


def test_abstract_action():
    class CustomActionBase(Action):
        @classmethod
        def name(cls):
            # Name method needed to test if base action was registered
            return "base_action"

        class Meta:
            abstract = True

        def run(self, dispatcher, tracker, domain):
            # custom run method
            return []

    class CustomAction(CustomActionBase):

        @classmethod
        def name(cls):
            return "custom_action"

    executor = ActionExecutor()
    executor.register_package('tests')
    assert CustomAction.name() in executor.actions
    assert CustomActionBase.name() not in executor.actions
