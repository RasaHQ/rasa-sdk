"""Configure gRPC DNS resolution before grpcio initializes."""

from __future__ import annotations

import os

_GRPC_DNS_RESOLVER_ENV = "GRPC_DNS_RESOLVER"
_NATIVE_RESOLVER = "native"
_applied = False


def ensure_native_grpc_dns_resolver() -> None:
    """Prefer the system resolver when grpcio's default c-ares resolver is unset.

    grpcio wheels bundle c-ares (including versions affected by CVE-2026-33630
    until grpcio ships a patched c-ares). Using the native resolver avoids
    c-ares DNS parsing when resolving OTLP and action-server gRPC hostnames.
    """
    global _applied
    if _applied:
        return
    if _GRPC_DNS_RESOLVER_ENV not in os.environ:
        os.environ[_GRPC_DNS_RESOLVER_ENV] = _NATIVE_RESOLVER
    _applied = True
