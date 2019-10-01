import logging

import rasa_sdk.version

logger = logging.getLogger(__name__)

__version__ = rasa_sdk.version.__version__

import rasa_sdk.cli
from rasa_sdk.interfaces import Tracker, Action, ActionExecutionRejection

if __name__ == "__main__":
    import rasa_sdk.__main__

    rasa_sdk.__main__.main()
