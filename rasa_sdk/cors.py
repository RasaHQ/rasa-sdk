r"""Cross-Origin Resource Sharing (CORS) support for the action server.

This module replaces the unmaintained ``sanic-cors`` package, which had no
release since 2022 and shipped CVE-2026-37737: its origin matching used
``re.match``, which anchors only at the start of the string, so a configured
origin of ``https://.*\.example\.com`` also accepted
``https://x.example.com.attacker.example``. Origins here are matched with
``re.fullmatch`` instead.

Only the subset of CORS the action server actually exposes is implemented.
The action server runs without credentials, so ``Access-Control-Allow-Origin``
may be the wildcard when no ``Origin`` header is present; when one is present
it is echoed back, which is what ``sanic-cors`` did.

Preflight (``OPTIONS``) requests are answered directly from request middleware
and never reach a route handler. Sanic resolves the route *before* running
middleware, but a routing failure is passed to
``Sanic.handle_exception(..., run_middleware=True)``, which falls back to the
app-level request middleware. That is why the middleware here is registered on
the app rather than on a blueprint: it is what lets a preflight to a
``POST``-only route, or to an unknown path, still receive a ``200``.
"""

from __future__ import annotations

import logging
import re
from typing import Any, List, Optional, Pattern, Text, Tuple, Union

from pydantic import BaseModel, ConfigDict
from sanic import Sanic
from sanic.request import Request
from sanic.response import HTTPResponse

logger = logging.getLogger(__name__)

ALLOW_ORIGIN_HEADER = "Access-Control-Allow-Origin"
ALLOW_METHODS_HEADER = "Access-Control-Allow-Methods"
ALLOW_HEADERS_HEADER = "Access-Control-Allow-Headers"
REQUEST_METHOD_HEADER = "Access-Control-Request-Method"
REQUEST_HEADERS_HEADER = "Access-Control-Request-Headers"
VARY_HEADER = "Vary"

WILDCARD = "*"

# The methods `sanic-cors` allowed by default, which the SDK never overrode.
ALLOWED_METHODS: Tuple[Text, ...] = (
    "DELETE",
    "GET",
    "HEAD",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
)
ALLOWED_METHODS_VALUE = ", ".join(ALLOWED_METHODS)

# Characters that made `sanic-cors` treat a configured origin as a regular
# expression. `*` is handled separately, as a glob.
_REGEX_METACHARACTERS = frozenset("\\[]()+|^$?{}")

_APP_POLICY_ATTRIBUTE = "cors_policy"
_APP_REGISTERED_ATTRIBUTE = "cors_middleware_registered"
_REQUEST_APPLIED_ATTRIBUTE = "cors_applied"


class CorsPolicy(BaseModel):
    """The set of origins the action server accepts cross-origin requests from."""

    model_config = ConfigDict(frozen=True)

    allow_all: bool = False
    literals: Tuple[Text, ...] = ()
    patterns: Tuple[Pattern[Text], ...] = ()

    def matches(self, request_origin: Text) -> bool:
        """Check whether a request's `Origin` header is allowed.

        Args:
            request_origin: The value of the request's `Origin` header.

        Returns:
            `True` if the origin is covered by this policy.
        """
        if self.allow_all:
            return True
        lowered = request_origin.lower()
        if any(lowered == literal.lower() for literal in self.literals):
            return True
        # `fullmatch` rather than `match` is the fix for CVE-2026-37737.
        return any(pattern.fullmatch(request_origin) for pattern in self.patterns)

    @property
    def origin_can_vary(self) -> bool:
        """Whether the emitted `Access-Control-Allow-Origin` depends on the request."""
        return self.allow_all or len(self.literals) > 1 or bool(self.patterns)

    @property
    def is_pattern_only(self) -> bool:
        """Whether this policy is made up exclusively of patterns."""
        return bool(self.patterns) and not self.literals and not self.allow_all


def _compile_glob(origin: Text) -> Pattern[Text]:
    """Translate a glob-style origin into a fully anchored regular expression.

    A `*` matches any run of characters that does not cross a `/`, so
    `https://*.example.com` accepts `https://a.example.com` and
    `https://a.b.example.com`, but neither
    `https://a.example.com.attacker.example` nor
    `https://attacker.example/.example.com`.

    Args:
        origin: A configured origin containing at least one `*`.

    Returns:
        The compiled, case-insensitive pattern.
    """
    parts = re.split(r"(\*)", origin)
    pattern = "".join(
        "[^/]*" if part == WILDCARD else re.escape(part) for part in parts
    )
    return re.compile(pattern, re.IGNORECASE)


def _compile_origin(origin: Text) -> Union[Text, Pattern[Text]]:
    """Turn one configured origin into a literal or a compiled pattern.

    Args:
        origin: A single entry from the configured origins.

    Returns:
        The origin itself if it should be compared literally, otherwise a
        compiled pattern to be matched with `re.fullmatch`.
    """
    if any(character in _REGEX_METACHARACTERS for character in origin):
        # `sanic-cors` accepted raw regular expressions here, so keep honouring
        # them -- anchored, unlike before.
        try:
            return re.compile(origin, re.IGNORECASE)
        except re.error as error:
            logger.warning(
                "Could not compile the configured CORS origin '%s' as a regular "
                "expression (%s). It will only be matched literally.",
                origin,
                error,
            )
            return origin
    if WILDCARD in origin:
        return _compile_glob(origin)
    return origin


def build_policy(cors_origins: Union[Text, List[Text], None]) -> CorsPolicy:
    """Build a `CorsPolicy` from a configured origin, or list of origins.

    Args:
        cors_origins: A single origin, a list of origins, or `None`. `"*"`
            anywhere in the list allows every origin.

    Returns:
        The resulting policy. An empty or unset configuration yields a policy
        that matches nothing.
    """
    if cors_origins is None:
        configured: List[Text] = []
    elif isinstance(cors_origins, str):
        configured = [cors_origins]
    else:
        configured = [str(origin) for origin in cors_origins]

    cleaned = [origin.strip() for origin in configured if origin and origin.strip()]
    if WILDCARD in cleaned:
        return CorsPolicy(allow_all=True)

    literals: List[Text] = []
    patterns: List[Pattern[Text]] = []
    for origin in cleaned:
        compiled = _compile_origin(origin)
        if isinstance(compiled, str):
            literals.append(compiled)
        else:
            patterns.append(compiled)
    return CorsPolicy(literals=tuple(literals), patterns=tuple(patterns))


def _read_origin(request: Request) -> Tuple[Optional[Text], bool]:
    """Read the request's `Origin` header.

    Args:
        request: The incoming request.

    Returns:
        A tuple of the origin (`None` when the header is absent or repeated)
        and whether the header was malformed, i.e. sent more than once.
    """
    origins = request.headers.getall("origin", None)
    if not origins:
        return None, False
    if len(origins) > 1:
        # Browsers send at most one `Origin`. `sanic-cors` joined repeats with
        # ", " and echoed the joined string back, which is never a valid origin.
        logger.debug("Received %s Origin headers; refusing CORS.", len(origins))
        return None, True
    return origins[0], False


def _is_preflight(request: Request) -> bool:
    """Check whether a request is a CORS preflight for an allowed method.

    Only such a request gets the `Access-Control-Allow-Methods` and
    `Access-Control-Allow-Headers` response headers. Every `OPTIONS` request is
    short-circuited regardless -- see `_cors_request_middleware`.

    Args:
        request: The incoming request.

    Returns:
        `True` for an `OPTIONS` request carrying an allowed
        `Access-Control-Request-Method`.
    """
    if request.method != "OPTIONS":
        return False
    requested_method = request.headers.get(REQUEST_METHOD_HEADER)
    if not requested_method:
        return False
    return requested_method.strip().upper() in ALLOWED_METHODS


def _add_vary_origin(response: HTTPResponse) -> None:
    """Append `Origin` to the response's `Vary` header without dropping values.

    Args:
        response: The response to amend.
    """
    existing = response.headers.get(VARY_HEADER)
    if not existing:
        response.headers[VARY_HEADER] = "Origin"
        return
    already_listed = {value.strip().lower() for value in existing.split(",")}
    if "origin" not in already_listed:
        response.headers[VARY_HEADER] = f"{existing}, Origin"


def _apply_cors_headers(
    request: Request, response: HTTPResponse, policy: CorsPolicy
) -> None:
    """Add the CORS response headers this request and policy call for.

    Args:
        request: The incoming request.
        response: The response to amend in place.
        policy: The app's configured policy.
    """
    request_origin, malformed_origin = _read_origin(request)
    if malformed_origin:
        # Emit nothing at all, so the browser blocks the response.
        return

    if request_origin is not None:
        if not policy.matches(request_origin):
            return
        response.headers[ALLOW_ORIGIN_HEADER] = request_origin
        if policy.origin_can_vary:
            _add_vary_origin(response)
    elif policy.allow_all:
        response.headers[ALLOW_ORIGIN_HEADER] = WILDCARD
    elif policy.is_pattern_only:
        # A pattern cannot be turned back into a concrete origin, so there is
        # nothing to advertise to a client that did not send one.
        return
    elif policy.literals:
        # No `Origin` header means this is not a cross-origin request at all,
        # so the value is inert. `sanic-cors` emitted the last of the sorted
        # literals here; kept as-is to avoid changing observable behaviour.
        response.headers[ALLOW_ORIGIN_HEADER] = sorted(policy.literals)[-1]
        if policy.origin_can_vary:
            _add_vary_origin(response)
    else:
        return

    if _is_preflight(request):
        response.headers[ALLOW_METHODS_HEADER] = ALLOWED_METHODS_VALUE
        requested_headers = request.headers.get(REQUEST_HEADERS_HEADER)
        if requested_headers:
            # The action server allowed any header, so echo back what was asked.
            response.headers[ALLOW_HEADERS_HEADER] = ", ".join(
                sorted(
                    header.strip()
                    for header in requested_headers.split(",")
                    if header.strip()
                )
            )


async def _cors_request_middleware(request: Request) -> Optional[HTTPResponse]:
    """Answer CORS preflight requests before they reach a route handler.

    Args:
        request: The incoming request.

    Returns:
        An empty `200` response for any `OPTIONS` request, otherwise `None` so
        that request handling continues as usual.
    """
    if request.method == "OPTIONS":
        # Every `OPTIONS` request is answered here, whether or not it carries a
        # usable `Access-Control-Request-Method`, and whether or not the route
        # would have accepted the method. The action server declares no
        # `OPTIONS` handlers of its own, so nothing is being shadowed.
        return HTTPResponse(status=200)
    return None


async def _cors_response_middleware(
    request: Request, response: Optional[HTTPResponse]
) -> None:
    """Add CORS headers to an outgoing response.

    Args:
        request: The request the response belongs to.
        response: The response to amend. `None` for websocket upgrades.
    """
    if response is None or not hasattr(response, "headers"):
        return

    policy: Optional[CorsPolicy] = getattr(request.app.ctx, _APP_POLICY_ATTRIBUTE, None)
    if policy is None:
        return

    # Sanic can run response middleware twice on the error path, once from
    # `handle_exception` and once from `Request.respond`.
    if getattr(request.ctx, _REQUEST_APPLIED_ATTRIBUTE, False):
        return
    setattr(request.ctx, _REQUEST_APPLIED_ATTRIBUTE, True)

    _apply_cors_headers(request, response, policy)


def configure_cors(
    app: Sanic, cors_origins: Union[Text, List[Text], None] = ""
) -> None:
    """Configure CORS origins for the given app.

    Safe to call more than once on the same app; the policy is replaced and the
    middleware stays registered exactly once.

    Args:
        app: The Sanic app to add CORS handling to.
        cors_origins: The allowed origins. `"*"` allows every origin; an empty
            value disables cross-origin requests.
    """
    setattr(app.ctx, _APP_POLICY_ATTRIBUTE, build_policy(cors_origins))

    if getattr(app.ctx, _APP_REGISTERED_ATTRIBUTE, False):
        return
    setattr(app.ctx, _APP_REGISTERED_ATTRIBUTE, True)

    # Sanic annotates these inconsistently, and differently between versions:
    # on 22.12 `on_request` is untyped, on 25.12 it is `on_response`. A
    # `type: ignore` correct on one is flagged as unused on the other, and this
    # module is backported to branches still on 22.12 - so go through a
    # deliberately untyped reference instead.
    middleware_registrar: Any = app
    middleware_registrar.on_request(_cors_request_middleware)
    middleware_registrar.on_response(_cors_response_middleware)
