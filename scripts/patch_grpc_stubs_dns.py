#!/usr/bin/env python3
"""Ensure generated gRPC stubs configure DNS before importing grpcio."""

from __future__ import annotations

from pathlib import Path

_STUB = Path("rasa_sdk/grpc_py/action_webhook_pb2_grpc.py")
_PREAMBLE = (
    "from rasa_sdk.grpc_dns import ensure_native_grpc_dns_resolver\n"
    "ensure_native_grpc_dns_resolver()\n"
)
_MARKER = "ensure_native_grpc_dns_resolver()"


def main() -> None:
    text = _STUB.read_text(encoding="utf-8")
    if _MARKER in text:
        return

    lines = text.splitlines(keepends=True)
    insert_at = 0
    for index, line in enumerate(lines):
        if line.startswith('"""') and line.count('"""') == 2:
            insert_at = index + 1
            break
        if line.startswith('"""'):
            for end in range(index + 1, len(lines)):
                if '"""' in lines[end]:
                    insert_at = end + 1
                    break
            break

    lines[insert_at:insert_at] = [_PREAMBLE]
    _STUB.write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
