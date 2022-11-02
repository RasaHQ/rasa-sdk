import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Text

import pytest
from pytest import LogCaptureFixture
from ruamel.yaml import YAMLError

import rasa_sdk.utils
from rasa_sdk.exceptions import (
    FileIOException,
    FileNotFoundException,
    YamlSyntaxException,
)
from rasa_sdk.utils import number_of_sanic_workers
from rasa_sdk.constants import (
    APPLICATION_ROOT_LOGGER_NAME,
    DEFAULT_SANIC_WORKERS,
    ENV_SANIC_WORKERS,
)


@pytest.fixture(autouse=True)
def reset_logging() -> None:
    manager = logging.root.manager
    manager.disabled = logging.NOTSET
    for logger in manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.setLevel(logging.NOTSET)
            logger.propagate = True
            logger.disabled = False
            logger.filters.clear()
            handlers = logger.handlers.copy()
            for handler in handlers:
                logger.removeHandler(handler)


def test_default_number_of_sanic_workers():
    n = number_of_sanic_workers()
    assert n == DEFAULT_SANIC_WORKERS


@pytest.mark.parametrize("n_workers", [3, 4, 1, 20])
def test_env_number_of_sanic_workers(n_workers):
    os.environ[ENV_SANIC_WORKERS] = str(n_workers)
    assert number_of_sanic_workers() == n_workers


@pytest.mark.parametrize("n_workers", [-1, 0, "fff"])
def test_invalid_env_number_of_sanic_workers(n_workers):
    os.environ[ENV_SANIC_WORKERS] = str(n_workers)
    assert number_of_sanic_workers() == DEFAULT_SANIC_WORKERS


async def test_call_maybe_coroutine_with_async() -> Any:
    expected = 5

    async def my_function():
        return expected

    actual = await rasa_sdk.utils.call_potential_coroutine(my_function())

    assert actual == expected


async def test_call_maybe_coroutine_with_sync() -> Any:
    expected = 5

    def my_function():
        return expected

    actual = await rasa_sdk.utils.call_potential_coroutine(my_function())

    assert actual == expected


def test_read_file_with_not_existing_path():
    with pytest.raises(FileNotFoundException):
        rasa_sdk.utils.read_file("some path")


def test_read_yaml_string():
    config = """
    user: user
    password: pass
    """
    content = rasa_sdk.utils.read_yaml(config)
    assert content["user"] == "user" and content["password"] == "pass"


def test_emojis_in_yaml():
    test_data = """
    data:
        - one 😁💯 👩🏿‍💻👨🏿‍💻
        - two £ (?u)\\b\\w+\\b f\u00fcr
    """
    content = rasa_sdk.utils.read_yaml(test_data)

    assert content["data"][0] == "one 😁💯 👩🏿‍💻👨🏿‍💻"
    assert content["data"][1] == "two £ (?u)\\b\\w+\\b für"


def test_read_file_with_wrong_encoding(tmp_path: Path):
    file = tmp_path / "myfile.txt"
    file.write_text("ä", encoding="latin-1")
    with pytest.raises(FileIOException):
        rasa_sdk.utils.read_file(file)


def test_read_yaml_raises_yaml_error():
    config = """
    user: user
        password: pass
    """
    with pytest.raises(YAMLError):
        rasa_sdk.utils.read_yaml(config)


def test_read_valid_yaml_file():
    root_dir = Path(__file__).resolve().parents[1]
    file = root_dir / "data/test_logging_config_files/test_valid_logging_config.yml"
    content = rasa_sdk.utils.read_yaml_file(file)

    assert content["version"] == 1
    assert content["handlers"]["test_handler"]["formatter"] == "customFormatter"
    assert content["loggers"]["rasa_sdk"]["handlers"][0] == "test_handler"


def test_read_invalid_yaml_file_raises():
    root_dir = Path(__file__).resolve().parents[1]
    file = root_dir / "data/test_invalid_yaml.yml"
    with pytest.raises(YamlSyntaxException):
        rasa_sdk.utils.read_yaml_file(file)


def test_valid_logging_configuration() -> None:
    root_dir = Path(__file__).resolve().parents[1]
    logging_config_file = (
        root_dir / "data/test_logging_config_files/test_valid_logging_config.yml"
    )
    rasa_sdk.utils.configure_logging_from_input_file(
        logging_config_file=logging_config_file
    )
    rasa_sdk_logger = logging.getLogger("rasa_sdk")

    handlers = rasa_sdk_logger.handlers
    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.FileHandler)
    assert "test_handler" == rasa_sdk_logger.handlers[0].name

    logging_message = "This is a test info log."
    rasa_sdk_logger.info(logging_message)

    handler_filename = handlers[0].baseFilename
    assert Path(handler_filename).exists()

    with open(handler_filename, "r") as logs:
        data = logs.readlines()
        logs_dict = json.loads(data[-1])
        assert logs_dict.get("message") == logging_message

        for key in ["time", "name", "levelname"]:
            assert key in logs_dict.keys()


@pytest.mark.parametrize(
    "logging_config_file",
    [
        "data/test_logging_config_files/test_missing_required_key_invalid_config.yml",
        "data/test_logging_config_files/test_invalid_value_for_level_in_config.yml",
        "data/test_logging_config_files/test_invalid_handler_key_in_config.yml",
    ],
)
def test_cli_invalid_logging_configuration(
    logging_config_file: Text, caplog: LogCaptureFixture
) -> None:
    root_dir = Path(__file__).resolve().parents[1]
    file = root_dir / logging_config_file
    with caplog.at_level(logging.DEBUG):
        rasa_sdk.utils.configure_logging_from_input_file(logging_config_file=file)

    assert (
        f"The logging config file {file} could not be applied "
        f"because it failed validation against the built-in Python "
        f"logging schema." in caplog.text
    )


@pytest.mark.skipif(
    sys.version_info.minor == 7, reason="no error is raised with python 3.7"
)
def test_cli_invalid_format_value_in_config(caplog: LogCaptureFixture) -> None:
    root_dir = Path(__file__).resolve().parents[1]
    logging_config_file = (
        root_dir
        / "data/test_logging_config_files/test_invalid_format_value_in_config.yml"
    )

    with caplog.at_level(logging.DEBUG):
        rasa_sdk.utils.configure_logging_from_input_file(
            logging_config_file=logging_config_file
        )

    assert (
        f"The logging config file {logging_config_file} could not be applied "
        f"because it failed validation against the built-in Python "
        f"logging schema." in caplog.text
    )


@pytest.mark.skipif(
    sys.version_info.minor == 9, reason="no error is raised with python 3.9"
)
def test_cli_non_existent_handler_id_in_config(caplog: LogCaptureFixture) -> None:
    root_dir = Path(__file__).resolve().parents[1]
    logging_config_file = (
        root_dir / "data/test_logging_config_files/test_non_existent_handler_id.yml"
    )

    with caplog.at_level(logging.DEBUG):
        rasa_sdk.utils.configure_logging_from_input_file(
            logging_config_file=logging_config_file
        )

    assert (
        f"The logging config file {logging_config_file} could not be applied "
        f"because it failed validation against the built-in Python "
        f"logging schema." in caplog.text
    )


def test_configure_default_logging():
    output_file = "test_default_logging.log"
    rasa_sdk.utils.configure_file_logging(
        logging.getLogger(APPLICATION_ROOT_LOGGER_NAME),
        output_file,
        logging.INFO,
        None,
    )
    rasa_sdk_logger = logging.getLogger("rasa_sdk")

    handlers = rasa_sdk_logger.handlers
    assert len(handlers) == 1
    handler = handlers[0]
    assert isinstance(handler, logging.FileHandler)

    logging_message = "Testing info log."
    rasa_sdk_logger.info(logging_message)

    handler_filename = handler.baseFilename
    assert Path(handler_filename).exists()
    assert Path(handler_filename).name == output_file

    with open(handler_filename, "r") as logs:
        data = logs.readlines()
        assert "[INFO ]  rasa_sdk  -  Testing info log." in data[-1]
