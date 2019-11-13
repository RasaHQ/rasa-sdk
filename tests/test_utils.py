import os
import pytest

from rasa_sdk.utils import number_of_sanic_workers
from rasa_sdk.constants import DEFAULT_SANIC_WORKERS, ENV_SANIC_WORKERS


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
