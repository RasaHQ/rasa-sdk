import importlib
import os

import rasa_sdk.grpc_dns as grpc_dns_module


def test_ensure_native_grpc_dns_resolver_sets_default(monkeypatch) -> None:
    monkeypatch.delenv("GRPC_DNS_RESOLVER", raising=False)
    importlib.reload(grpc_dns_module)

    grpc_dns_module.ensure_native_grpc_dns_resolver()

    assert os.environ["GRPC_DNS_RESOLVER"] == "native"


def test_ensure_native_grpc_dns_resolver_respects_existing_value(monkeypatch) -> None:
    monkeypatch.setenv("GRPC_DNS_RESOLVER", "ares")
    importlib.reload(grpc_dns_module)

    grpc_dns_module.ensure_native_grpc_dns_resolver()

    assert os.environ["GRPC_DNS_RESOLVER"] == "ares"
