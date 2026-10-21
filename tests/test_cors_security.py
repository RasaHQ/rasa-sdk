import re

import sanic_cors.core as cors_core

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
