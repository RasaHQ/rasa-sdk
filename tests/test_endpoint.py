import pytest
import json

import rasa_sdk.endpoint as ep

app = ep.create_app("actions.act")


def test_server_health_returns_200():
    request, response = app.test_client.get("/health")
    assert response.status == 200
    assert response.json == {"status": "ok"}


def test_server_list_actions_returns_200():
    request, response = app.test_client.get("/actions")
    assert response.status == 200
    assert len(response.json) == 2


def test_server_webhook_unknown_action_returns_404():
    data = {
        "next_action": "test_action_1",
        "tracker": {"sender_id": "1", "conversation_id": "default"},
    }
    request, response = app.test_client.post("/webhook", data=json.dumps(data))
    assert response.status == 404


def test_server_webhook_custom_action_returns_200():
    data = {
        "next_action": "custom_action",
        "tracker": {"sender_id": "1", "conversation_id": "default"},
    }
    request, response = app.test_client.post("/webhook", data=json.dumps(data))
    assert response.status == 200


def test_server_webhook_custom_async_action_returns_200():
    data = {
        "next_action": "custom_async_action",
        "tracker": {"sender_id": "1", "conversation_id": "default"},
    }
    request, response = app.test_client.post("/webhook", data=json.dumps(data))
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
