from typing import Any, Dict, List, Optional, Text
import json
import logging
import pickle
import zlib
from pathlib import Path

import pytest
from pytest import MonkeyPatch
from sanic import Sanic
from sanic.http.tls.context import SanicSSLContext

import rasa_sdk.endpoint as ep
from rasa_sdk.events import SlotSet
from tests.conftest import get_stack


logger = logging.getLogger(__name__)

# Shared by gRPC TLS integration tests; reused here for HTTPS startup pickling.
_SSL_CERT = Path("integration_tests/grpc_server/setup/certs/server.pem")
_SSL_KEY = Path("integration_tests/grpc_server/setup/certs/server-key.pem")


def _capture_sanic_serve(monkeypatch: MonkeyPatch) -> Dict[Text, Any]:
    """Stub ``Sanic.serve`` and return a dict of captured kwargs."""
    captured: Dict[Text, Any] = {}

    def fake_serve(
        *,
        primary: Optional[Sanic] = None,
        app_loader: Any = None,
        **_kwargs: Any,
    ) -> None:
        captured["primary"] = primary
        captured["app_loader"] = app_loader

    monkeypatch.setattr(ep.Sanic, "serve", fake_serve)
    return captured


def _ssl_payload_sanic_would_pickle(ssl_config: Any) -> Any:
    """Apply the same SSL rewrite Sanic.serve does before spawning workers."""
    if isinstance(ssl_config, SanicSSLContext):
        return ssl_config.sanic
    return ssl_config


@pytest.fixture
def action_executor() -> ep.ActionExecutor:
    _executor = ep.ActionExecutor()
    _executor.register_package("tests")
    return _executor


@pytest.fixture
def sanic_app(action_executor: ep.ActionExecutor) -> Sanic:
    return ep.create_app(action_executor)


def test_server_health_returns_200(sanic_app: Sanic):
    _request, response = sanic_app.test_client.get("/health")
    assert response.status == 200
    assert response.json == {"status": "ok"}


def test_server_list_actions_returns_200(
    sanic_app: Sanic,
):
    """Test that the server returns a list of actions."""
    # When we request the list of actions
    _request, response = sanic_app.test_client.get("/actions")

    # Then the server should return a list of actions
    assert response.status == 200
    assert len(response.json) == 11
    expected = [
        # defined in tests/conftest.py
        {"name": "custom_async_action"},
        {"name": "custom_action"},
        {"name": "custom_action_exception"},
        {"name": "custom_action_with_dialogue_stack"},
        {"name": "subclass_test_action_a"},
        # defined in tests/test_executor.py
        {"name": "action_streaming"},
        {"name": "action_missing_stream_end"},
        {"name": "mock_validation_action"},
        {"name": "mock_form_validation_action"},
        # defined in tests/test_forms.py
        {"name": "some_form"},
        # defined in tests/conftest.py
        {"name": "subclass_test_action_b"},
    ]
    assert response.json == expected


def test_server_webhook_unknown_action_returns_404(
    sanic_app: Sanic,
):
    data = {
        "next_action": "non_existing_action",
        "tracker": {"sender_id": "1", "conversation_id": "default"},
    }
    _request, response = sanic_app.test_client.post("/webhook", data=json.dumps(data))
    assert response.status == 404


def test_server_webhook_handles_action_exception(
    sanic_app: Sanic,
):
    data = {
        "next_action": "custom_action_exception",
        "tracker": {"sender_id": "1", "conversation_id": "default"},
        "domain": {},
    }
    _request, response = sanic_app.test_client.post("/webhook", data=json.dumps(data))
    assert response.status == 500
    assert response.json.get("error") == "test exception"
    assert response.json.get("request_body") == data


def test_server_webhook_custom_action_returns_200(
    sanic_app: Sanic,
):
    data = {
        "next_action": "custom_action",
        "tracker": {"sender_id": "1", "conversation_id": "default"},
        "domain": {},
    }
    _request, response = sanic_app.test_client.post("/webhook", data=json.dumps(data))
    events = response.json.get("events")

    assert events == [SlotSet("test", "bar")]
    assert response.status == 200


def test_server_webhook_custom_async_action_returns_200(sanic_app: Sanic):
    data = {
        "next_action": "custom_async_action",
        "tracker": {"sender_id": "1", "conversation_id": "default"},
        "domain": {},
    }
    _request, response = sanic_app.test_client.post("/webhook", data=json.dumps(data))
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

    _request, response = sanic_app.test_client.post(
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


def test_run_app_loader_factory_is_picklable(
    monkeypatch: MonkeyPatch,
    action_executor: ep.ActionExecutor,
) -> None:
    """Sanic.serve pickles AppLoader when spawning workers.

    Nested factories defined inside ``run()`` are not picklable and crash
    action-server startup (``Can't pickle local object 'run.<locals>._app_factory'``).
    """
    captured = _capture_sanic_serve(monkeypatch)

    ep.run(action_executor, port=5099)

    app_loader = captured.get("app_loader")
    assert app_loader is not None
    assert app_loader.factory is not None

    # Round-trip through pickle the same way Sanic's multiprocess manager does.
    restored_loader = pickle.loads(pickle.dumps(app_loader))
    restored_app = restored_loader.load()
    assert restored_app.name == "rasa_sdk"


def test_run_ssl_config_is_picklable(
    monkeypatch: MonkeyPatch,
    action_executor: ep.ActionExecutor,
) -> None:
    """Sanic.serve pickles server SSL settings when spawning workers.

    A live ``ssl.SSLContext`` from ``create_ssl_context()`` is not picklable and
    crashes HTTPS action-server startup
    (``TypeError: cannot pickle 'SSLContext' object``). Sanic only rewrites the
    value to a picklable cert/key dict when it is already a ``SanicSSLContext``.
    """
    assert _SSL_CERT.is_file(), f"missing test cert: {_SSL_CERT}"
    assert _SSL_KEY.is_file(), f"missing test key: {_SSL_KEY}"

    captured = _capture_sanic_serve(monkeypatch)

    ep.run(
        action_executor,
        port=5099,
        ssl_certificate=str(_SSL_CERT),
        ssl_keyfile=str(_SSL_KEY),
    )

    primary = captured.get("primary")
    assert primary is not None
    assert primary.state.ssl is not None

    ssl_payload = _ssl_payload_sanic_would_pickle(primary.state.ssl)
    pickle.loads(pickle.dumps(ssl_payload))
