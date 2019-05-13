import rasa_sdk
import sys
import warnings

# this makes sure old code can still import from `rasa_core_sdk`
# although the package has been moved to `rasa_sdk`
sys.modules["rasa_core_sdk"] = rasa_sdk

warnings.warn(
    "The 'rasa_core_sdk' package has been renamed. You should change "
    "your imports to use 'rasa_sdk' instead.",
    UserWarning,
)
