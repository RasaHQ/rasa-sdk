import re
from typing import Any, Dict, List, Optional, Text, Union

import pytest
from sanic import Sanic, response
from sanic.compat import Header
from sanic.request import Request
from sanic.response import HTTPResponse
from sanic_testing.testing import SanicASGITestClient

from rasa_sdk.cors import (
    ALLOWED_METHODS_VALUE,
    _cors_response_middleware,
    build_policy,
    configure_cors,
)

CORS_HEADERS = (
    "access-control-allow-origin",
    "access-control-allow-credentials",
    "access-control-expose-headers",
    "access-control-allow-methods",
    "access-control-allow-headers",
    "access-control-max-age",
)

WILDCARD_ORIGIN = "*"
LITERAL_ORIGIN = "https://app.example.com"
GLOB_ORIGIN = "https://*.example.com"
# The form `sanic-cors` accepted as a raw regular expression.
REGEX_ORIGIN = r"https://.*\.example\.com"


def _app_name(request: Any) -> Text:
    """Derive a valid, unique Sanic app name from the calling test."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", request.node.name)


def _build_app(
    name: Text,
    cors_origins: Union[Text, List[Text], None],
    preset_vary: Optional[Text] = None,
) -> Sanic:
    """Create a small app configured the way the action server is."""
    Sanic.test_mode = True
    app = Sanic(name)
    configure_cors(app, cors_origins)

    @app.get("/read")
    async def read(request: Request) -> HTTPResponse:
        payload = response.text("ok")
        if preset_vary:
            payload.headers["Vary"] = preset_vary
        return payload

    @app.post("/webhook")
    async def webhook(request: Request) -> HTTPResponse:
        return response.json({"ok": True})

    @app.get("/boom")
    async def boom(request: Request) -> HTTPResponse:
        raise ValueError("boom")

    return app


def _client(
    request: Any,
    cors_origins: Union[Text, List[Text], None],
    preset_vary: Optional[Text] = None,
) -> SanicASGITestClient:
    return _build_app(_app_name(request), cors_origins, preset_vary).asgi_client


def _cors_headers(payload: Any) -> Dict[Text, Text]:
    return {
        key.lower(): value
        for key, value in payload.headers.items()
        if key.lower() in CORS_HEADERS
    }


# --------------------------------------------------------------------------
# Origin matching
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "configured, request_origin, expected",
    [
        (LITERAL_ORIGIN, LITERAL_ORIGIN, True),
        (LITERAL_ORIGIN, "https://APP.EXAMPLE.COM", True),
        (LITERAL_ORIGIN, "https://other.example.com", False),
        # a literal origin is never treated as a pattern
        ("https://a.b-c.example.com", "https://aXb-c.example.com", False),
        (WILDCARD_ORIGIN, "https://anything.test", True),
        (GLOB_ORIGIN, "https://a.example.com", True),
        (GLOB_ORIGIN, "https://a.b.example.com", True),
        (GLOB_ORIGIN, "https://example.com", False),
        (REGEX_ORIGIN, "https://a.example.com", True),
        (REGEX_ORIGIN, "https://a.other.com", False),
        ("", LITERAL_ORIGIN, False),
        (None, LITERAL_ORIGIN, False),
        ([], LITERAL_ORIGIN, False),
    ],
)
def test_policy_matches_origin(
    configured: Union[Text, List[Text], None], request_origin: Text, expected: bool
) -> None:
    assert build_policy(configured).matches(request_origin) is expected


@pytest.mark.parametrize(
    "configured, attacker_origin",
    [
        # CVE-2026-37737: `sanic-cors` matched with `re.match`, which anchors
        # only at the start, so an attacker-registered suffix domain was
        # accepted. All of these must now be rejected.
        (REGEX_ORIGIN, "https://a.example.com.attacker.test"),
        (GLOB_ORIGIN, "https://a.example.com.attacker.test"),
        (LITERAL_ORIGIN, f"{LITERAL_ORIGIN}.attacker.test"),
        # a glob must not be satisfied by putting the trusted name in a path
        (GLOB_ORIGIN, "https://attacker.test/a.example.com"),
    ],
)
def test_policy_rejects_suffix_and_path_bypass(
    configured: Text, attacker_origin: Text
) -> None:
    assert build_policy(configured).matches(attacker_origin) is False


def test_policy_ignores_blank_entries() -> None:
    policy = build_policy(["", "  ", LITERAL_ORIGIN])

    assert policy.literals == (LITERAL_ORIGIN,)
    assert policy.matches(LITERAL_ORIGIN) is True


def test_policy_allows_everything_when_wildcard_is_one_of_many() -> None:
    assert build_policy([LITERAL_ORIGIN, WILDCARD_ORIGIN]).allow_all is True


def test_policy_falls_back_to_literal_for_uncompilable_origin() -> None:
    policy = build_policy(["https://[unclosed"])

    assert policy.patterns == ()
    assert policy.matches("https://[unclosed") is True
    assert policy.matches("https://anything") is False


# --------------------------------------------------------------------------
# Response headers
# --------------------------------------------------------------------------


async def test_matching_origin_is_echoed(request: Any) -> None:
    _, payload = await _client(request, WILDCARD_ORIGIN).get(
        "/read", headers={"Origin": "https://a.test"}
    )

    assert _cors_headers(payload) == {"access-control-allow-origin": "https://a.test"}
    assert payload.headers["Vary"] == "Origin"


async def test_non_matching_origin_gets_no_cors_headers(request: Any) -> None:
    _, payload = await _client(request, LITERAL_ORIGIN).get(
        "/read", headers={"Origin": "https://evil.test"}
    )

    assert payload.status == 200
    assert _cors_headers(payload) == {}


async def test_request_without_origin_gets_wildcard_for_open_policy(
    request: Any,
) -> None:
    # The action server runs without credentials, so unlike the Rasa server it
    # may answer with the wildcard when no `Origin` was sent.
    _, payload = await _client(request, WILDCARD_ORIGIN).get("/read")

    assert _cors_headers(payload)["access-control-allow-origin"] == WILDCARD_ORIGIN
    assert "Vary" not in payload.headers


async def test_unset_policy_emits_nothing(request: Any) -> None:
    _, payload = await _client(request, "").get("/read")

    assert _cors_headers(payload) == {}


async def test_credentials_are_never_advertised(request: Any) -> None:
    # The action server does not enable `supports_credentials`.
    _, payload = await _client(request, WILDCARD_ORIGIN).get(
        "/read", headers={"Origin": "https://a.test"}
    )

    assert "access-control-allow-credentials" not in _cors_headers(payload)


async def test_repeated_origin_header_is_rejected(request: Any) -> None:
    _, payload = await _client(request, WILDCARD_ORIGIN).get(
        "/read", headers=[("Origin", "https://a.test"), ("Origin", "https://b.test")]
    )

    assert _cors_headers(payload) == {}


async def test_single_allowed_origin_does_not_add_vary(request: Any) -> None:
    _, payload = await _client(request, LITERAL_ORIGIN).get(
        "/read", headers={"Origin": LITERAL_ORIGIN}
    )

    assert "Vary" not in payload.headers


async def test_vary_origin_is_appended_to_existing_value(request: Any) -> None:
    _, payload = await _client(
        request, WILDCARD_ORIGIN, preset_vary="Accept-Encoding"
    ).get("/read", headers={"Origin": "https://a.test"})

    assert payload.headers["Vary"] == "Accept-Encoding, Origin"


@pytest.mark.parametrize("status_path", ["/boom", "/does-not-exist"])
async def test_error_responses_still_carry_cors_headers(
    request: Any, status_path: Text
) -> None:
    _, payload = await _client(request, WILDCARD_ORIGIN).get(
        status_path, headers={"Origin": "https://a.test"}
    )

    assert payload.status >= 400
    assert _cors_headers(payload)["access-control-allow-origin"] == "https://a.test"


# --------------------------------------------------------------------------
# Preflight handling
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path, requested_method",
    [
        # `/webhook` declares no OPTIONS handler ...
        ("/webhook", "POST"),
        ("/read", "GET"),
        # ... and this path does not exist at all
        ("/does-not-exist", "GET"),
    ],
)
async def test_preflight_is_answered_without_reaching_a_handler(
    request: Any, path: Text, requested_method: Text
) -> None:
    _, payload = await _client(request, WILDCARD_ORIGIN).options(
        path,
        headers={
            "Origin": "https://a.test",
            "Access-Control-Request-Method": requested_method,
        },
    )

    assert payload.status == 200
    assert payload.text == ""
    headers = _cors_headers(payload)
    assert headers["access-control-allow-origin"] == "https://a.test"
    assert headers["access-control-allow-methods"] == ALLOWED_METHODS_VALUE


async def test_preflight_echoes_requested_headers(request: Any) -> None:
    _, payload = await _client(request, WILDCARD_ORIGIN).options(
        "/webhook",
        headers={
            "Origin": "https://a.test",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Custom, authorization",
        },
    )

    assert (
        _cors_headers(payload)["access-control-allow-headers"]
        == "X-Custom, authorization"
    )


@pytest.mark.parametrize(
    "extra_headers",
    [{}, {"Access-Control-Request-Method": "TRACE"}],
)
async def test_options_without_valid_preflight_still_returns_200(
    request: Any, extra_headers: Dict[Text, Text]
) -> None:
    # `sanic-cors` short-circuited every OPTIONS request, not only well-formed
    # preflights. Keep doing so, but without advertising the allowed methods.
    _, payload = await _client(request, WILDCARD_ORIGIN).options(
        "/webhook", headers={"Origin": "https://a.test", **extra_headers}
    )

    assert payload.status == 200
    headers = _cors_headers(payload)
    assert headers["access-control-allow-origin"] == "https://a.test"
    assert "access-control-allow-methods" not in headers


async def test_max_age_is_not_advertised(request: Any) -> None:
    # `sanic-cors` emitted the literal string "None" here.
    _, payload = await _client(request, WILDCARD_ORIGIN).options(
        "/webhook",
        headers={"Origin": "https://a.test", "Access-Control-Request-Method": "POST"},
    )

    assert "access-control-max-age" not in _cors_headers(payload)


# --------------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------------


async def test_websocket_upgrade_is_left_alone(request: Any) -> None:
    # A websocket handler produces no `HTTPResponse`; the middleware must not
    # raise when there is nothing to annotate.
    app = _build_app(_app_name(request), WILDCARD_ORIGIN)
    upgrade_request = Request(
        b"/websocket",
        Header({"Origin": "https://a.test"}),
        "1.1",
        "GET",
        None,
        app,
    )

    assert await _cors_response_middleware(upgrade_request, None) is None


async def test_reconfiguring_replaces_policy_without_duplicating_headers(
    request: Any,
) -> None:
    app = _build_app(_app_name(request), LITERAL_ORIGIN)
    configure_cors(app, "https://second.example.com")

    _, payload = await app.asgi_client.get(
        "/read", headers={"Origin": "https://second.example.com"}
    )

    assert payload.headers.get_list("Access-Control-Allow-Origin") == [
        "https://second.example.com"
    ]
    _, blocked = await app.asgi_client.get("/read", headers={"Origin": LITERAL_ORIGIN})
    assert _cors_headers(blocked) == {}
