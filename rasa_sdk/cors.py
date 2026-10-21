"""Harden Sanic-Cors origin matching for CVE-2026-37737."""

from __future__ import annotations

import re
from typing import Any

_patched = False


def ensure_sanic_cors_origin_anchor_fix() -> None:
    """Anchor regex CORS origin checks so trusted origins cannot be prefix-bypassed."""
    global _patched
    if _patched:
        return

    import sanic_cors.core as cors_core

    def try_match(request_origin: Any, maybe_regex: Any) -> bool:
        if isinstance(maybe_regex, cors_core.RegexObject):
            return re.fullmatch(maybe_regex, request_origin) is not None
        if cors_core.probably_regex(maybe_regex):
            return (
                re.fullmatch(maybe_regex, request_origin, flags=re.IGNORECASE)
                is not None
            )
        try:
            return request_origin.lower() == maybe_regex.lower()
        except AttributeError:
            return request_origin == maybe_regex

    cors_core.try_match = try_match
    _patched = True
