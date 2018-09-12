from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import importlib
import inspect
import logging
import pkgutil

import six
from typing import Text, List, Dict, Any

from rasa_core_sdk import utils, Action, Tracker
from rasa_core_sdk.slots import Slot

logger = logging.getLogger(__name__)


class InputValidator(object):
    def __init__(self):
        self.validators = {}

    def register_slot(self, slot):
        if inspect.isclass(slot):
            if slot.__module__.startswith("rasa_core."):
                logger.warning("Skipping built in Slot {}.".format(action))
                return
            else:
                slot = slot()
        if isinstance(slot, Slot):
            self.register_function(slot.name(), slot.validate)
        else:
            raise Exception("You can only register instances or subclasses of "
                            "type Slot. If you want to directly register "
                            "a function, use `register_function` instead.")


    def register_function(self, name, f):
        logger.info("Registered function for '{}'.".format(name))
        valid_keys = utils.arguments_of(f)
        if len(valid_keys) < 1:
            raise Exception("You can only register functions that take "
                            "1 parameters as arguments. Your function accepts only {} "
                            "parameters.".format(len(valid_keys)))
        self.validators[name] = f
        
    def _import_submodules(self, package, recursive=True):
        """ Import all submodules of a module, recursively, including
        subpackages

        :param package: package (name or actual module)
        :type package: str | module
        :rtype: dict[str, types.ModuleType]
        """
        if isinstance(package, six.string_types):
            package = importlib.import_module(package)
        if not getattr(package, '__path__', None):
            return

        results = {}
        for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
            full_name = package.__name__ + '.' + name
            results[full_name] = importlib.import_module(full_name)
            if recursive and is_pkg:
                self._import_submodules(full_name)

    def register_package(self, package):
        try:
            self._import_submodules(package)
        except ImportError:
            logger.exception("Failed to register package '{}'."
                             "".format(package))

        slots = utils.all_subclasses(Slot)

        for slot in slots:
            if (not slot.__module__.startswith("rasa_core.") and
                    not slot.__module__.startswith("rasa_core_sdk.")):
                self.register_slot(slot)


    def validate(self, data):
        slot_name = data.get("slot")
        if slot_name:
            logger.debug("Received request to validate '{}'".format(slot_name))
            validator = self.validators.get(slot_name)
            if not validator:
                raise Exception("No registered Validator found for name '{}'."
                                "".format(slot_name))

            parse_data = data.get("parse_data")
            new_parse_data = validator(parse_data)
            logger.debug("Successfully validated '{}'".format(slot_name))
            return new_parse_data
        else:
            logger.warning("Received an action call without an action.")
