import asyncio
import inspect
import logging
import logging.config
import warnings
import os
from pathlib import Path
from ruamel import yaml as yaml
from ruamel.yaml import YAMLError
from ruamel.yaml.constructor import DuplicateKeyError

from typing import (
    AbstractSet,
    Any,
    ClassVar,
    Dict,
    List,
    Text,
    Optional,
    Coroutine,
    Union,
)

import rasa_sdk

from rasa_sdk.constants import (
    DEFAULT_ENCODING,
    DEFAULT_SANIC_WORKERS,
    ENV_SANIC_WORKERS,
    DEFAULT_LOG_LEVEL_LIBRARIES,
    ENV_LOG_LEVEL_LIBRARIES,
    PYTHON_LOGGING_SCHEMA_DOCS,
    YAML_VERSION,
)
from rasa_sdk.exceptions import (
    FileIOException,
    FileNotFoundException,
    YamlSyntaxException,
)

logger = logging.getLogger(__name__)


class Element(dict):
    """Represents an element in a list of elements in a rich message."""

    __acceptable_keys: ClassVar[List[Text]] = [
        "title",
        "item_url",
        "image_url",
        "subtitle",
        "buttons",
    ]

    def __init__(self, *args, **kwargs):
        """Initializes an element in a list of elements in a rich message."""
        kwargs = {
            key: value for key, value in kwargs.items() if key in self.__acceptable_keys
        }

        super().__init__(*args, **kwargs)


class Button(dict):
    """Represents a button in a rich message."""

    pass


class Singleton(type):
    """Singleton metaclass."""

    _instances: ClassVar[Dict[Any, Any]] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """Call the class.

        Args:
            *args: Arguments.
            **kwargs: Keyword arguments.
        """
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)

        return cls._instances[cls]

    @classmethod
    def clear(cls) -> None:
        """Clear the class."""
        cls._instances = {}


def all_subclasses(cls: Any) -> List[Any]:
    """Returns all known (imported) subclasses of a class."""
    return cls.__subclasses__() + [
        g for s in cls.__subclasses__() for g in all_subclasses(s)
    ]


def add_logging_level_option_arguments(parser):
    """Add options to an argument parser to configure logging levels."""
    # arguments for logging configuration
    parser.add_argument(
        "-v",
        "--verbose",
        help="Be verbose. Sets logging level to INFO",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
        default=logging.INFO,
    )
    parser.add_argument(
        "-vv",
        "--debug",
        help="Print lots of debugging statements. Sets logging level to DEBUG",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
    )
    parser.add_argument(
        "--quiet",
        help="Be quiet! Sets logging level to WARNING",
        action="store_const",
        dest="loglevel",
        const=logging.WARNING,
    )


def add_logging_file_arguments(parser):
    """Add options to an argument parser to configure logging to a file."""
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Store logs in specified file.",
    )
    parser.add_argument(
        "--logging-config_file",
        type=str,
        default=None,
        help="If set, the name of the logging configuration file will be set "
        "to the given name.",
    )


def configure_colored_logging(loglevel):
    """Configure logging with colors."""
    import coloredlogs

    field_styles = coloredlogs.DEFAULT_FIELD_STYLES.copy()
    field_styles["asctime"] = {}
    level_styles = coloredlogs.DEFAULT_LEVEL_STYLES.copy()
    level_styles["debug"] = {}
    coloredlogs.install(
        level=loglevel,
        use_chroot=False,
        fmt="%(asctime)s %(levelname)-8s %(name)s  - %(message)s",
        level_styles=level_styles,
        field_styles=field_styles,
    )


def configure_logging_from_input_file(logging_config_file: Union[Path, Text]) -> None:
    """Parses YAML file content to configure logging.

    Args:
        logging_config_file: YAML file containing logging configuration to handle
            custom formatting
    """
    logging_config_dict = read_yaml_file(logging_config_file)

    try:
        logging.config.dictConfig(logging_config_dict)
    except (ValueError, TypeError, AttributeError, ImportError) as e:
        logging.debug(
            f"The logging config file {logging_config_file} could not "
            f"be applied because it failed validation against "
            f"the built-in Python logging schema. "
            f"More info at {PYTHON_LOGGING_SCHEMA_DOCS}.",
            exc_info=e,
        )


def set_default_logging(
    logger_obj: logging.Logger, output_log_file: Optional[Text], loglevel: int
) -> None:
    """Configure default logging to a file.

    :param logger_obj: Logger object to configure.
    :param output_log_file: Path of log file to write to.
    :param loglevel: Log Level.
    :return: None.
    """
    if not output_log_file:
        return

    if not loglevel:
        loglevel = logging.INFO

    logger_obj.setLevel(loglevel)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-5.5s]  %(name)s  -  %(message)s"
    )
    file_handler = logging.FileHandler(output_log_file, encoding=DEFAULT_ENCODING)
    file_handler.setLevel(loglevel)
    file_handler.setFormatter(formatter)
    logger_obj.addHandler(file_handler)


def configure_file_logging(
    logger_obj: logging.Logger,
    output_log_file: Optional[Text],
    loglevel: int,
    logging_config_file: Optional[Text],
) -> None:
    """Configure logging configuration.

    :param logger_obj: Logger object to configure.
    :param output_log_file: Path of log file to write to.
    :param loglevel: Log Level.
    :param logging_config_file: YAML file containing logging configuration to handle
            custom formatting
    :return: None.
    """
    if logging_config_file is not None:
        configure_logging_from_input_file(logging_config_file)
        return

    set_default_logging(logger_obj, output_log_file, loglevel)


def arguments_of(func) -> AbstractSet[Text]:
    """Return the parameters of the function `func` as a list of their names."""
    return inspect.signature(func).parameters.keys()


def number_of_sanic_workers() -> int:
    """Get the number of Sanic workers to use in `app.run()`.

    If the environment variable `constants.ENV_SANIC_WORKERS`
    is set and is not equal to 1.
    """

    def _log_and_get_default_number_of_workers():
        logger.debug(
            f"Using the default number of Sanic workers ({DEFAULT_SANIC_WORKERS})."
        )
        return DEFAULT_SANIC_WORKERS

    try:
        env_value = int(os.environ.get(ENV_SANIC_WORKERS, DEFAULT_SANIC_WORKERS))
    except ValueError:
        logger.error(
            f"Cannot convert environment variable `{ENV_SANIC_WORKERS}` "
            f"to int ('{os.environ[ENV_SANIC_WORKERS]}')."
        )
        return _log_and_get_default_number_of_workers()

    if env_value == DEFAULT_SANIC_WORKERS:
        return _log_and_get_default_number_of_workers()

    if env_value < 1:
        warnings.warn(
            f"Cannot set number of Sanic workers to the desired value "
            f"({env_value}). The number of workers must be at least 1."
        )
        return _log_and_get_default_number_of_workers()

    logger.debug(f"Using {env_value} Sanic workers.")
    return env_value


def check_version_compatibility(rasa_version: Optional[Text]) -> None:
    """Check if the version of rasa and rasa_sdk are compatible.

    The version check relies on the version string being formatted as
    'x.y.z' and compares whether the numbers x and y are the same for both
    rasa and rasa_sdk.

    Args:
        rasa_version: A string containing the version of rasa that
                        is making the call to the action server.

    Raises:
        Warning: The version of rasa version unknown or not compatible with
                    this version of rasa_sdk.
    """
    # Check for versions of Rasa that are too old to report their version number
    if rasa_version is None:
        warnings.warn(
            f"You are using an old version of rasa which might "
            f"not be compatible with this version of rasa_sdk "
            f"({rasa_sdk.__version__}).\n"
            f"To ensure compatibility use the same version "
            f"for both, modulo the last number, i.e. using version "
            f"A.B.x the numbers A and B should be identical for "
            f"both rasa and rasa_sdk."
        )
        return

    rasa = rasa_version.split(".")[:-1]
    sdk = rasa_sdk.__version__.split(".")[:-1]

    if rasa != sdk:
        warnings.warn(
            f"Your versions of rasa and "
            f"rasa_sdk might not be compatible. You "
            f"are currently running rasa version {rasa_version} "
            f"and rasa_sdk version {rasa_sdk.__version__}.\n"
            f"To ensure compatibility use the same "
            f"version for both, modulo the last number, "
            f"i.e. using version A.B.x the numbers A and "
            f"B should be identical for "
            f"both rasa and rasa_sdk."
        )


def update_sanic_log_level() -> None:
    """Set the log level of sanic loggers.

    Use the environment variable 'LOG_LEVEL_LIBRARIES', or default to
    `DEFAULT_LOG_LEVEL_LIBRARIES` if undefined.
    """
    from sanic.log import logger, error_logger, access_logger

    log_level = os.environ.get(ENV_LOG_LEVEL_LIBRARIES, DEFAULT_LOG_LEVEL_LIBRARIES)

    logger.setLevel(log_level)
    error_logger.setLevel(log_level)
    access_logger.setLevel(log_level)

    logger.propagate = False
    error_logger.propagate = False
    access_logger.propagate = False


async def call_potential_coroutine(
    coroutine_or_return_value: Union[Any, Coroutine],
) -> Any:
    """Await if it's a coroutine."""
    if asyncio.iscoroutine(coroutine_or_return_value):
        return await coroutine_or_return_value

    return coroutine_or_return_value


def read_file(filename: Union[Text, Path], encoding: Text = DEFAULT_ENCODING) -> Any:
    """Read text from a file."""
    try:
        with open(filename, encoding=encoding) as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundException(
            f"Failed to read file, " f"'{os.path.abspath(filename)}' does not exist."
        )
    except UnicodeDecodeError:
        raise FileIOException(
            f"Failed to read file '{os.path.abspath(filename)}', "
            f"could not read the file using {encoding} to decode "
            f"it. Please make sure the file is stored with this "
            f"encoding."
        )


def read_yaml(content: Text, reader_type: Text = "safe") -> Any:
    """Parses yaml from a text.

    Args:
        content: A text containing yaml content.
        reader_type: Reader type to use. By default, "safe" will be used.

    Raises:
        ruamel.yaml.parser.ParserError: If there was an error when parsing the YAML.
    """
    if _is_ascii(content):
        # Required to make sure emojis are correctly parsed
        content = (
            content.encode("utf-8")
            .decode("raw_unicode_escape")
            .encode("utf-16", "surrogatepass")
            .decode("utf-16")
        )

    yaml_parser = yaml.YAML(typ=reader_type)
    yaml_parser.version = YAML_VERSION
    yaml_parser.preserve_quotes = True

    return yaml_parser.load(content) or {}


def _is_ascii(text: Text) -> bool:
    return all(ord(character) < 128 for character in text)


def read_yaml_file(filename: Union[Text, Path]) -> Dict[Text, Any]:
    """Parses a yaml file.

    Raises an exception if the content of the file can not be parsed as YAML.

    Args:
        filename: The path to the file which should be read.

    Returns:
        Parsed content of the file.
    """
    try:
        return read_yaml(read_file(filename, DEFAULT_ENCODING))
    except (YAMLError, DuplicateKeyError) as e:
        raise YamlSyntaxException(filename, e)


def file_as_bytes(file_path: Text) -> bytes:
    """Read in a file as a byte array.

    Args:
        file_path: Path to the file to read.

    Returns:
        The file content as a byte array.

    Raises:
        FileNotFoundException: If the file does not exist.
    """
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundException(
            f"Failed to read file, " f"'{os.path.abspath(file_path)}' does not exist."
        )
