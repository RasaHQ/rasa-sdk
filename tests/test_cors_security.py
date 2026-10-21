import re

import sanic_cors.core as cors_core
import sanic_cors.extension as cors_extension
from sanic import Sanic, response
from sanic_cors import CORS

from rasa_sdk.cors import ensure_sanic_cors_origin_anchor_fix


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


def test_cors_middleware_does_not_reflect_prefix_bypass_origin() -> None:
    ensure_sanic_cors_origin_anchor_fix()

    app = Sanic("cors-security-test")
    CORS(
        app,
        resources={r"/*": {"origins": r"https://trusted\.example\.com"}},
        automatic_options=True,
    )

    @app.get("/")
    async def handler(_request):
        return response.text("ok")

    _, preflight = app.test_client.options(
        "/",
        headers={
            "Origin": "https://trusted.example.com.attacker.io",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert (
        preflight.headers.get("Access-Control-Allow-Origin")
        != "https://trusted.example.com.attacker.io"
    )
