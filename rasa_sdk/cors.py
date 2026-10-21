"""Harden Sanic-Cors origin matching for CVE-2026-37737."""

from __future__ import annotations

import re
import sys
from typing import Any, Callable

_patched = False


def ensure_sanic_cors_origin_anchor_fix() -> None:
    """Anchor regex CORS origin checks so trusted origins cannot be prefix-bypassed."""
    global _patched
    if _patched:
        return

    import importlib

    importlib.import_module("sanic_cors.decorator")
    importlib.import_module("sanic_cors.extension")
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

    _rebind_sanic_cors_try_match(try_match)
    _patched = True


def _rebind_sanic_cors_try_match(try_match: Callable[..., bool]) -> None:
    """Rebind ``try_match`` everywhere Sanic-Cors copied it from ``core``."""
    for module_name, module in list(sys.modules.items()):
        if (
            module_name == "sanic_cors" or module_name.startswith("sanic_cors.")
        ) and hasattr(module, "try_match"):
            setattr(module, "try_match", try_match)
