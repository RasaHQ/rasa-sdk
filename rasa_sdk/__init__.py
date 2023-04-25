import logging

import rasa_sdk.cli
import rasa_sdk.version
import rasa_sdk.plugin
from rasa_sdk.interfaces import Tracker, Action, ActionExecutionRejection  # noqa: F401
from rasa_sdk.forms import ValidationAction, FormValidationAction  # noqa: F401

logger = logging.getLogger(__name__)

__version__ = rasa_sdk.version.__version__

if __name__ == "__main__":
    import rasa_sdk.__main__

    rasa_sdk.__main__.main()
