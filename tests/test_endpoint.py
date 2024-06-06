from typing import Any, Dict, List, Text
import json
import logging
import zlib

import pytest
from sanic import Sanic

import rasa_sdk.endpoint as ep
from rasa_sdk.events import SlotSet
from tests.conftest import get_stack


logger = logging.getLogger(__name__)


@pytest.fixture
def sanic_app():
    return ep.create_app("tests")


def test_endpoint_exit_for_unknown_actions_package():
    with pytest.raises(SystemExit):
        ep.create_app("non-existing-actions-package")


def test_server_health_returns_200(sanic_app: Sanic):
    request, response = sanic_app.test_client.get("/health")
    assert response.status == 200
    assert response.json == {"status": "ok"}


def test_server_list_actions_returns_200(sanic_app: Sanic):
    request, response = sanic_app.test_client.get("/actions")
    assert response.status == 200
    assert len(response.json) == 9
    print(response.json)
    expected = [
        # defined in tests/conftest.py
        {"name": "custom_async_action"},
        {"name": "custom_action"},
        {"name": "custom_action_exception"},
        {"name": "custom_action_with_dialogue_stack"},
        {"name": "subclass_test_action_a"},
        {"name": "mock_validation_action"},
        {"name": "mock_form_validation_action"},
        # defined in tests/test_forms.py
        {"name": "some_form"},
        # defined in tests/conftest.py
        {"name": "subclass_test_action_b"},
    ]
    assert response.json == expected


def test_server_webhook_unknown_action_returns_404(sanic_app: Sanic):
    data = {
        "next_action": "test_action_1",
        "tracker": {"sender_id": "1", "conversation_id": "default"},
    }
    request, response = sanic_app.test_client.post("/webhook", data=json.dumps(data))
    assert response.status == 404


def test_server_webhook_handles_action_exception(sanic_app: Sanic):
    data = {
        "next_action": "custom_action_exception",
        "tracker": {"sender_id": "1", "conversation_id": "default"},
        "domain": {},
    }
    request, response = sanic_app.test_client.post("/webhook", data=json.dumps(data))
    assert response.status == 500
    assert response.json.get("error") == "test exception"
    assert response.json.get("request_body") == data


def test_server_webhook_custom_action_returns_200(sanic_app: Sanic):
    data = {
        "next_action": "custom_action",
        "tracker": {"sender_id": "1", "conversation_id": "default"},
        "domain": {},
    }
    request, response = sanic_app.test_client.post("/webhook", data=json.dumps(data))
    events = response.json.get("events")

    assert events == [SlotSet("test", "bar")]
    assert response.status == 200


def test_server_webhook_custom_async_action_returns_200(sanic_app: Sanic):
    data = {
        "next_action": "custom_async_action",
        "tracker": {"sender_id": "1", "conversation_id": "default"},
        "domain": {},
    }
    request, response = sanic_app.test_client.post("/webhook", data=json.dumps(data))
    events = response.json.get("events")

    assert events == [SlotSet("test", "foo"), SlotSet("test2", "boo")]
    assert response.status == 200


def test_arg_parser_actions_params_folder_style():
    parser = ep.create_argument_parser()
    args = ["--actions", "actions/act"]

    with pytest.raises(BaseException) as e:
        parser.parse_args(args)
    if e is not None:
        assert True
    else:
        assert False


def test_arg_parser_actions_params_module_style():
    parser = ep.create_argument_parser()
    args = ["--actions", "actions.act"]
    cmdline_args = parser.parse_args(args)
    assert cmdline_args.actions == "actions.act"


def test_server_webhook_custom_action_encoded_data_returns_200(sanic_app: Sanic):
    data = {
        "next_action": "custom_action",
        "tracker": {"sender_id": "1", "conversation_id": "default"},
        "domain": {"intents": ["greet", "goodbye"]},
    }

    request, response = sanic_app.test_client.post(
        "/webhook",
        data=zlib.compress(json.dumps(data).encode()),
        headers={"Content-encoding": "deflate"},
    )
    events = response.json.get("events")

    assert events == [SlotSet("test", "bar")]
    assert response.status == 200


@pytest.mark.parametrize(
    "stack_state, dialogue_stack",
    [
        ({}, []),
        ({"stack": get_stack()}, get_stack()),
    ],
)
def test_server_webhook_custom_action_with_dialogue_stack_returns_200(
    stack_state: Dict[Text, Any],
    dialogue_stack: List[Dict[Text, Any]],
    sanic_app: Sanic,
):
    data = {
        "next_action": "custom_action_with_dialogue_stack",
        "tracker": {"sender_id": "1", "conversation_id": "default", **stack_state},
        "domain": {},
    }
    _, response = sanic_app.test_client.post("/webhook", data=json.dumps(data))
    events = response.json.get("events")

    assert events == [SlotSet("stack", dialogue_stack)]
    assert response.status == 200
