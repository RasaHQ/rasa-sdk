import re

import sanic_cors.core as cors_core
import sanic_cors.extension as cors_extension
from sanic import Sanic, response

from rasa_sdk.cors import ensure_sanic_cors_origin_anchor_fix
from rasa_sdk.endpoint import configure_cors


def test_sanic_cors_origin_anchor_fix_blocks_prefix_bypass() -> None:
    ensure_sanic_cors_origin_anchor_fix()

    trusted_pattern = r"https://trusted\.example\.com"
    attacker_origin = "https://trusted.example.com.attacker.io"

    assert cors_core.try_match(attacker_origin, trusted_pattern) is False
    assert cors_core.try_match("https://trusted.example.com", trusted_pattern) is True


def test_sanic_cors_origin_anchor_fix_allows_exact_string_origins() -> None:
    ensure_sanic_cors_origin_anchor_fix()

    assert cors_core.try_match("https://foo.com", "https://foo.com") is True
    assert cors_core.try_match("https://foo.com.evil", "https://foo.com") is False


def test_sanic_cors_origin_anchor_fix_supports_compiled_patterns() -> None:
    ensure_sanic_cors_origin_anchor_fix()

    pattern = re.compile(r"https://trusted\.example\.com")
    assert cors_core.try_match("https://trusted.example.com.evil", pattern) is False


def test_sanic_cors_extension_module_uses_anchored_try_match() -> None:
    ensure_sanic_cors_origin_anchor_fix()

    trusted_pattern = r"https://trusted\.example\.com"
    attacker_origin = "https://trusted.example.com.attacker.io"

    assert cors_extension.try_match(attacker_origin, trusted_pattern) is False
    assert cors_extension.try_match is cors_core.try_match
    assert cors_extension.try_match("/health", "/.*") is True


def test_cors_middleware_anchors_regex_origins() -> None:
    app = Sanic("cors-security-test")

    @app.get("/health")
    async def health(_request):
        return response.json({"status": "ok"})

    configure_cors(app, r"https://trusted\.example\.com")

    attacker_origin = "https://trusted.example.com.attacker.io"
    trusted_origin = "https://trusted.example.com"

    _, blocked = app.test_client.get("/health", headers={"Origin": attacker_origin})
    assert blocked.status == 200
    assert blocked.headers.get("Access-Control-Allow-Origin") != attacker_origin

    _, allowed = app.test_client.get("/health", headers={"Origin": trusted_origin})
    assert allowed.status == 200
    assert allowed.headers.get("Access-Control-Allow-Origin") == trusted_origin
