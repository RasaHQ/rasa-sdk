import logging

import rasa_sdk.cli
import rasa_sdk.version

logger = logging.getLogger(__name__)

__version__ = rasa_sdk.version.__version__

if __name__ == "__main__":
    import rasa_sdk.__main__

    rasa_sdk.__main__.main()
