from __future__ import annotations
import importlib
import inspect
import logging
import pkgutil
import warnings
from typing import Text, List, Dict, Any, Type, Union, Callable, Optional, Set, cast
from collections import namedtuple
import types
import sys
import os

from pydantic import BaseModel, Field

from rasa_sdk.interfaces import (
    Tracker,
    ActionNotFoundException,
    Action,
    ActionMissingDomainException,
)

from rasa_sdk import utils

logger = logging.getLogger(__name__)


class CollectingDispatcher:
    """Send messages back to user."""

    def __init__(self) -> None:
        """Create a `CollectingDispatcher` object."""
        self.messages: List[Dict[Text, Any]] = []

    def utter_message(
        self,
        text: Optional[Text] = None,
        image: Optional[Text] = None,
        json_message: Optional[Dict[Text, Any]] = None,
        template: Optional[Text] = None,
        response: Optional[Text] = None,
        attachment: Optional[Text] = None,
        buttons: Optional[List[Dict[Text, Any]]] = None,
        elements: Optional[List[Dict[Text, Any]]] = None,
        **kwargs: Any,
    ) -> None:
        """Send a text to the output channel."""
        if template and not response:
            response = template
            warnings.warn(
                "Please pass the parameter `response` instead of `template` "
                "to `utter_message`. `template` will be deprecated in Rasa 3.0.0. ",
                FutureWarning,
            )
        message = {
            "text": text,
            "buttons": buttons or [],
            "elements": elements or [],
            "custom": json_message or {},
            "template": response,
            "response": response,
            "image": image,
            "attachment": attachment,
        }
        message.update(kwargs)

        self.messages.append(message)

    # deprecated
    def utter_custom_message(self, *elements: Dict[Text, Any], **kwargs: Any) -> None:
        """Sends a message with custom elements to the output channel.

        Deprecated:
            Use `utter_message(elements=<list of elements>)` instead.

        Args:
            elements: List of elements to be sent to the output channel.
            kwargs: Additional parameters to be sent to the output channel.
        """
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
            "Use `utter_message(template=<template name>, buttons=<list of buttons>)`"
            " instead.",
            FutureWarning,
        )

        self.utter_message(template=template, buttons=buttons, **kwargs)

    # noinspection PyUnusedLocal
    def utter_template(
        self, template: Text, tracker: Tracker, silent_fail: bool = False, **kwargs: Any
    ) -> None:
        """Send a message to the client based on a template."""
        warnings.warn(
            "Use of `utter_template` is deprecated. "
            "Use `utter_message(response=<template_name>)` instead.",
            FutureWarning,
        )

        self.utter_message(response=template, **kwargs)

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


TimestampModule = namedtuple("TimestampModule", ["timestamp", "module"])


class ActionExecutorRunResult(BaseModel):
    """Model for action executor run result."""

    events: List[Dict[Text, Any]] = Field(alias="events")
    responses: List[Dict[Text, Any]] = Field(alias="responses")


class ActionExecutor:
    """Executes actions."""

    def __init__(self) -> None:
        """Initializes the `ActionExecutor`."""
        self.actions: Dict[Text, Callable] = {}
        self._modules: Dict[Text, TimestampModule] = {}
        self._loaded: Set[Type[Action]] = set()
        self.domain: Optional[Dict[Text, Any]] = None
        self.domain_digest: Optional[Text] = None

    def register_action(self, action: Union[Type[Action], Action]) -> None:
        """Register an action with the executor.

        Args:
            action: Action to be registered. It can either be an instance of
            `Action` subclass class or an actual `Action` subclass.
        """
        if inspect.isclass(action):
            action = cast(Type[Action], action)
            if action.__module__.startswith("rasa."):
                logger.warning(f"Skipping built in Action {action}.")
                return
            else:
                # Check if this class has already been loaded in the past.
                if action in self._loaded:
                    return

                # Mark the class as "loaded"
                self._loaded.add(action)
                action = action()

        if isinstance(action, Action):
            self.register_function(action.name(), action.run)
        else:
            raise Exception(
                "You can only register instances or subclasses of "
                "type Action. If you want to directly register "
                "a function, use `register_function` instead."
            )

    def register_function(self, action_name: Text, f: Callable) -> None:
        """Register an executor function for an action.

        Args:
            action_name: Name of the action.
            f: Function to be registered.
        """
        valid_keys = utils.arguments_of(f)
        if len(valid_keys) < 3:
            raise Exception(
                "You can only register functions that take "
                "3 parameters as arguments. The three parameters "
                "your function will receive are: dispatcher, "
                f"tracker, domain. Your function accepts only {len(valid_keys)} "
                "parameters."
            )

        if action_name in self.actions:
            logger.info(f"Re-registered function for '{action_name}'.")
        else:
            logger.info(f"Registered function for '{action_name}'.")

        self.actions[action_name] = f

    def _import_submodules(
        self, package: Union[Text, types.ModuleType], recursive: bool = True
    ) -> None:
        """Import a module, or a package and its submodules recursively.

        Args:
            package: Package or module name, or an already loaded Python module.
            recursive: If `True`, and `package` is a package, import all of its
                sub-packages as well.
        """
        if isinstance(package, str):
            package = self._import_module(package)

        if not getattr(package, "__path__", None):
            return

        for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
            full_name = package.__name__ + "." + name
            self._import_module(full_name)

            if recursive and is_pkg:
                self._import_submodules(full_name)

    def _import_module(self, name: Text) -> types.ModuleType:
        """Import a Python module. If possible, register the file where it came from.

        Args:
            name: The module's name using Python's module path syntax.

        Returns:
            The loaded module.
        """
        module = importlib.import_module(name)

        module_file = getattr(module, "__file__", None)
        if module_file:
            # If the module we're importing is a namespace package (a package
            # without __init__.py), then there's nothing to watch for the
            # package itself.
            timestamp = os.path.getmtime(module_file)
            self._modules[module_file] = TimestampModule(timestamp, module)

        return module

    def register_package(self, package: Union[Text, types.ModuleType]) -> None:
        """Register all the `Action` subclasses contained in a Python module or package.

        If an `ImportError` is raised when loading the module or package, the
        action server is stopped with exit code 1.

        Args:
            package: Module or package name, or an already loaded Python module.
        """
        try:
            self._import_submodules(package)
        except ImportError:
            logger.exception(f"Failed to register package '{package}'.")
            sys.exit(1)

        self._register_all_actions()

    def _register_all_actions(self) -> None:
        """Scan for all user subclasses of `Action`, and register them."""
        import inspect

        actions = utils.all_subclasses(Action)

        for action in actions:
            if (
                not action.__module__.startswith("rasa_core.")
                and not action.__module__.startswith("rasa.")
                and not action.__module__.startswith("rasa_sdk.")
                and not action.__module__.startswith("rasa_core_sdk.")
                and not inspect.isabstract(action)
            ):
                self.register_action(action)

    def _find_modules_to_reload(self) -> Dict[Text, TimestampModule]:
        """Finds all Python modules that should be reloaded.

         Reloads modules by checking their files' timestamps.

        Returns:
            Dictionary containing file paths, new timestamps and Python modules
            that should be reloaded.
        """
        to_reload = {}

        for path, (timestamp, module) in self._modules.items():
            try:
                new_timestamp = os.path.getmtime(path)
            except OSError:
                # Ignore missing files
                continue

            if new_timestamp > timestamp:
                to_reload[path] = TimestampModule(new_timestamp, module)

        return to_reload

    def reload(self) -> None:
        """Reload all Python modules that have been loaded in the past.

        To check if a module should be reloaded, the file's last timestamp is
        checked against the current one. If the current last-modified timestamp
        is larger than the previous one, the module is re-imported using
        `importlib.reload`.

        If one or more modules are reloaded during this process, the entire
        `Action` class hierarchy is scanned again to see what new classes can
        be registered.
        """
        to_reload = self._find_modules_to_reload()
        any_module_reloaded = False

        for path, (timestamp, module) in to_reload.items():
            try:
                new_module = importlib.reload(module)
                self._modules[path] = TimestampModule(timestamp, new_module)
                logger.info(
                    f"Reloaded module/package: '{module.__name__}' "
                    f"(file: '{os.path.relpath(path)}')"
                )
                any_module_reloaded = True
            except (SyntaxError, ImportError):
                logger.exception(
                    f"Error while reloading module/package: '{module.__name__}' "
                    f"(file: '{os.path.relpath(path)}'):"
                )
                logger.info("Please fix the error(s) in the Python file and try again.")

        if any_module_reloaded:
            self._register_all_actions()

    @staticmethod
    def _create_api_response(
        events: List[Dict[Text, Any]], messages: List[Dict[Text, Any]]
    ) -> ActionExecutorRunResult:
        return ActionExecutorRunResult(events=events, responses=messages)

    @staticmethod
    def validate_events(
        events: List[Dict[Text, Any]],
        action_name: Text,
    ) -> List[Dict[Text, Any]]:
        """Validate the events returned by the action.

        Args:
            events: List of events returned by the action.

            action_name: Name of the action that should be executed.

        Returns:
            List of validated events.
        """
        validated = []
        for event in events:
            if isinstance(event, dict):
                if not event.get("event"):
                    logger.error(
                        f"Your action '{action_name}' returned an action dict "
                        "without the `event` property. Please use "
                        "the helpers in `rasa_sdk.events`! Event will"
                        f"be ignored!"
                    )
                    logger.debug(f"Contents of ignored event: '{event}'")
                else:
                    validated.append(event)
            elif type(event).__module__ == "rasa.core.events":
                warnings.warn(
                    "Your action should not return Rasa actions within the "
                    "SDK. Instead of using events from "
                    "`rasa.core.events`, you should use the ones "
                    "provided in `rasa_sdk.events`! "
                    "We will try to make this work, but this "
                    "might go wrong!"
                )
                validated.append(event.as_dict())
            else:
                logger.error(
                    f"Your action's '{action_name}' run method returned an invalid "
                    f"event. Event will be ignored."
                )
                logger.debug(f"Contents of ignored event: '{event}'")
                # we won't append this to validated events -> will be ignored
        return validated

    def is_domain_digest_valid(self, domain_digest: Optional[Text]) -> bool:
        """Check if the domain_digest is valid.

        If the domain_digest is empty or different from the one provided, it is invalid.

        Args:
            domain_digest: latest value provided to compare the current value with.

        Returns:
            True if the domain_digest is valid, False otherwise.
        """
        return bool(self.domain_digest) and self.domain_digest == domain_digest

    def update_and_return_domain(
        self, payload: Dict[Text, Any], action_name: Text
    ) -> Optional[Dict[Text, Any]]:
        """Validate the digest, store the domain if available, and return the domain.

        This method validates the domain digest from the payload.
        If the digest is invalid and no domain is provided, an exception is raised.
        If domain data is available, it stores the domain and digest.
        Finally, it returns the domain.

        Args:
            payload: Request payload containing the domain data.
            action_name: Name of the action that should be executed.

        Returns:
            The domain dictionary.

        Raises:
            ActionMissingDomainException: Invalid digest and no domain data available.
        """
        payload_domain = payload.get("domain")
        payload_domain_digest = payload.get("domain_digest")

        # If digest is invalid and no domain is available - raise the error
        if (
            not self.is_domain_digest_valid(payload_domain_digest)
            and payload_domain is None
        ):
            raise ActionMissingDomainException(action_name)

        if payload_domain:
            self.domain = payload_domain
            self.domain_digest = payload_domain_digest

        return self.domain

    async def run(
        self,
        action_call: Dict[Text, Any],
    ) -> Optional[ActionExecutorRunResult]:
        """Run the action and return the response.

        Args:
            action_call: Request payload containing the action data.

        Returns:
            Response containing the events and messages or None if
            the action does not exist.
        """
        from rasa_sdk.interfaces import Tracker

        action_name = action_call.get("next_action")
        if action_name:
            logger.debug(f"Received request to run '{action_name}'")
            action = self.actions.get(action_name)
            if not action:
                raise ActionNotFoundException(action_name)

            tracker_json = action_call["tracker"]
            domain = self.update_and_return_domain(action_call, action_name)
            tracker = Tracker.from_dict(tracker_json)
            dispatcher = CollectingDispatcher()

            events = await utils.call_potential_coroutine(
                action(dispatcher, tracker, domain)
            )

            if not events:
                # make sure the action did not just return `None`...
                events = []

            validated_events = self.validate_events(events, action_name)
            logger.debug(f"Finished running '{action_name}'")
            return self._create_api_response(validated_events, dispatcher.messages)

        logger.warning("Received an action call without an action.")
        return None

    def list_actions(self) -> List[ActionName]:
        """List all registered action names."""
        return [ActionName(name=action_name) for action_name in self.actions.keys()]


class ActionName(BaseModel):
    """Model for action name."""

    name: str = Field(alias="name")
