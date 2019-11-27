import importlib
import inspect
import logging
import pkgutil
import warnings
from typing import Text, List, Dict, Any, Type, Union, Callable, Optional
import typing
import types

from rasa_sdk.interfaces import Tracker, ActionNotFoundException

from rasa_sdk import utils

if typing.TYPE_CHECKING:
    from rasa_sdk.interfaces import Action

logger = logging.getLogger(__name__)


class CollectingDispatcher:
    """Send messages back to user"""

    def __init__(self) -> None:

        self.messages = []

    def utter_message(
        self,
        text: Optional[Text] = None,
        image: Optional[Text] = None,
        json_message: Optional[Dict[Text, Any]] = None,
        template: Optional[Text] = None,
        attachment: Optional[Text] = None,
        buttons: Optional[List[Dict[Text, Any]]] = None,
        elements: Optional[List[Dict[Text, Any]]] = None,
        **kwargs: Any,
    ) -> None:
        """"Send a text to the output channel"""

        message = {
            "text": text,
            "buttons": buttons or [],
            "elements": elements or [],
            "custom": json_message or {},
            "template": template,
            "image": image,
            "attachment": attachment,
        }
        message.update(kwargs)

        self.messages.append(message)

    # deprecated
    def utter_custom_message(self, *elements: Dict[Text, Any], **kwargs: Any) -> None:
        warnings.warn(
            "Use of `utter_custom_message` is deprecated. "
            "Use `utter_message(elements=<list of elements>)` instead.",
            FutureWarning,
        )
        self.utter_message(elements=list(elements), **kwargs)

    def utter_elements(self, *elements: Dict[Text, Any], **kwargs: Any) -> None:
        """Sends a message with custom elements to the output channel."""
        warnings.warn(
            "Use of `utter_elements` is deprecated. "
            "Use `utter_message(elements=<list of elements>)` instead.",
            FutureWarning,
        )
        self.utter_message(elements=list(elements), **kwargs)

    def utter_button_message(
        self, text: Text, buttons: List[Dict[Text, Any]], **kwargs: Any
    ) -> None:
        """Sends a message with buttons to the output channel."""
        warnings.warn(
            "Use of `utter_button_message` is deprecated. "
            "Use `utter_message(text=<text> , buttons=<list of buttons>)` instead.",
            FutureWarning,
        )

        self.utter_message(text=text, buttons=buttons, **kwargs)

    def utter_attachment(self, attachment: Text, **kwargs: Any) -> None:
        """Send a message to the client with attachments."""
        warnings.warn(
            "Use of `utter_attachment` is deprecated. "
            "Use `utter_message(attachment=<attachment>)` instead.",
            FutureWarning,
        )

        self.utter_message(attachment=attachment, **kwargs)

    # noinspection PyUnusedLocal
    def utter_button_template(
        self,
        template: Text,
        buttons: List[Dict[Text, Any]],
        tracker: Tracker,
        silent_fail: bool = False,
        **kwargs: Any,
    ) -> None:
        """Sends a message template with buttons to the output channel."""
        warnings.warn(
            "Use of `utter_button_template` is deprecated. "
            "Use `utter_message(template=<template name>, buttons=<list of buttons>)` instead.",
            FutureWarning,
        )

        self.utter_message(template=template, buttons=buttons, **kwargs)

    # noinspection PyUnusedLocal
    def utter_template(
        self, template: Text, tracker: Tracker, silent_fail: bool = False, **kwargs: Any
    ) -> None:
        """"Send a message to the client based on a template."""
        warnings.warn(
            "Use of `utter_template` is deprecated. "
            "Use `utter_message(template=<template_name>)` instead.",
            FutureWarning,
        )

        self.utter_message(template=template, **kwargs)

    def utter_custom_json(self, json_message: Dict[Text, Any], **kwargs: Any) -> None:
        """Sends custom json to the output channel."""
        warnings.warn(
            "Use of `utter_custom_json` is deprecated. "
            "Use `utter_message(json_message=<message dict>)` instead.",
            FutureWarning,
        )

        self.utter_message(json_message=json_message, **kwargs)

    def utter_image_url(self, image: Text, **kwargs: Any) -> None:
        """Sends url of image attachment to the output channel."""
        warnings.warn(
            "Use of `utter_image_url` is deprecated. "
            "Use `utter_message(image=<image url>)` instead.",
            FutureWarning,
        )

        self.utter_message(image=image, **kwargs)


class ActionExecutor:
    def __init__(self):
        self.actions = {}

    def register_action(self, action: Union[Type["Action"], "Action"]) -> None:
        from rasa_sdk.interfaces import Action

        if inspect.isclass(action):
            if action.__module__.startswith("rasa."):
                logger.warning(f"Skipping built in Action {action}.")
                return
            else:
                action = action()
        if isinstance(action, Action):
            self.register_function(action.name(), action.run)
        else:
            raise Exception(
                "You can only register instances or subclasses of "
                "type Action. If you want to directly register "
                "a function, use `register_function` instead."
            )

    def register_function(self, name: Text, f: Callable) -> None:
        logger.info(f"Registered function for '{name}'.")
        valid_keys = utils.arguments_of(f)
        if len(valid_keys) < 3:
            raise Exception(
                "You can only register functions that take "
                "3 parameters as arguments. The three parameters "
                "your function will receive are: dispatcher, "
                f"tracker, domain. Your function accepts only {len(valid_keys)} "
                "parameters."
            )
        self.actions[name] = f

    def _import_submodules(
        self, package: Union[Text, types.ModuleType], recursive: bool = True
    ) -> None:
        """ Import all submodules of a module, recursively, including
        subpackages

        :param package: package (name or actual module)
        :type package: str | module
        :rtype: dict[str, types.ModuleType]
        """
        if isinstance(package, str):
            package = importlib.import_module(package)
        if not getattr(package, "__path__", None):
            return

        results = {}
        for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
            full_name = package.__name__ + "." + name
            results[full_name] = importlib.import_module(full_name)
            if recursive and is_pkg:
                self._import_submodules(full_name)

    def register_package(self, package: Union[Text, types.ModuleType]) -> None:
        from rasa_sdk.interfaces import Action

        try:
            self._import_submodules(package)
        except ImportError:
            logger.exception(f"Failed to register package '{package}'.")

        actions = utils.all_subclasses(Action)

        for action in actions:
            meta = action.__dict__.get("Meta", False)
            abstract = getattr(meta, "abstract", False)
            if (
                not action.__module__.startswith("rasa_core.")
                and not action.__module__.startswith("rasa.")
                and not action.__module__.startswith("rasa_sdk.")
                and not action.__module__.startswith("rasa_core_sdk.")
                and not abstract
            ):
                self.register_action(action)

    @staticmethod
    def _create_api_response(
        events: List[Dict[Text, Any]], messages: List[Dict[Text, Any]]
    ) -> Dict[Text, Any]:
        return {"events": events, "responses": messages}

    @staticmethod
    def validate_events(events: List[Dict[Text, Any]], action_name: Text):
        validated = []
        for e in events:
            if isinstance(e, dict):
                if not e.get("event"):
                    logger.error(
                        f"Your action '{action_name}' returned an action dict "
                        "without the `event` property. Please use "
                        "the helpers in `rasa_sdk.events`! Event will"
                        f"be ignored! Event: {e}"
                    )
                else:
                    validated.append(e)
            elif type(e).__module__ == "rasa.core.events":
                logger.warning(
                    "Your action should not return Rasa actions within the "
                    "SDK. Instead of using events from "
                    "`rasa.core.events`, you should use the ones "
                    "provided in `rasa_sdk.events`! "
                    "We will try to make this work, but this "
                    "might go wrong!"
                )
                validated.append(e.as_dict())
            else:
                logger.error(
                    f"Your action's '{action_name}' run method returned an invalid "
                    f"event. Event will be ignored. Event: '{e}'."
                )
                # we won't append this to validated events -> will be ignored
        return validated

    async def run(self, action_call: Dict[Text, Any]) -> Optional[Dict[Text, Any]]:
        from rasa_sdk.interfaces import Tracker

        action_name = action_call.get("next_action")
        if action_name:
            logger.debug(f"Received request to run '{action_name}'")
            action = self.actions.get(action_name)
            if not action:
                raise ActionNotFoundException(action_name)

            tracker_json = action_call.get("tracker")
            domain = action_call.get("domain", {})
            tracker = Tracker.from_dict(tracker_json)
            dispatcher = CollectingDispatcher()

            if utils.is_coroutine_action(action):
                events = await action(dispatcher, tracker, domain)
            else:
                events = action(dispatcher, tracker, domain)

            if not events:
                # make sure the action did not just return `None`...
                events = []

            validated_events = self.validate_events(events, action_name)
            logger.debug(f"Finished running '{action_name}'")
            return self._create_api_response(validated_events, dispatcher.messages)
        else:
            logger.warning("Received an action call without an action.")
