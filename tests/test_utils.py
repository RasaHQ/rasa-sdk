import os

from rasa_sdk.utils import number_of_sanic_workers
from rasa_sdk.constants import DEFAULT_SANIC_WORKERS, ENV_SANIC_WORKERS


def test_default_number_of_sanic_workers():
    n = number_of_sanic_workers()
    assert n == DEFAULT_SANIC_WORKERS


def test_env_number_of_sanic_workers():
    os.environ[ENV_SANIC_WORKERS] = "5"
    n = number_of_sanic_workers()
    assert n == 5


def test_invalid_env_number_of_sanic_workers():
    os.environ[ENV_SANIC_WORKERS] = "0"
    n = number_of_sanic_workers()
    assert n == DEFAULT_SANIC_WORKERS
