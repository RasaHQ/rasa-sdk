"""Configure gRPC DNS resolution before grpcio initializes."""

from __future__ import annotations

import os

_GRPC_DNS_RESOLVER_ENV = "GRPC_DNS_RESOLVER"
_NATIVE_RESOLVER = "native"
_applied = False


def ensure_native_grpc_dns_resolver() -> None:
    """Prefer the system resolver when grpcio's default c-ares resolver is unset.

    grpcio wheels bundle c-ares; using the native resolver avoids known c-ares
    DNS parsing vulnerabilities when resolving OTLP collector hostnames.
    """
    global _applied
    if _applied:
        return
    if _GRPC_DNS_RESOLVER_ENV not in os.environ:
        os.environ[_GRPC_DNS_RESOLVER_ENV] = _NATIVE_RESOLVER
    _applied = True
