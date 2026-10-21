import importlib
import os
import subprocess
import sys
from pathlib import Path

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


def test_generated_stub_configures_dns_before_importing_grpc() -> None:
    source = (
        Path(__file__).parents[1] / "rasa_sdk/grpc_py/action_webhook_pb2_grpc.py"
    ).read_text(encoding="utf-8")

    assert source.index("ensure_native_grpc_dns_resolver()") < source.index(
        "import grpc"
    )


def test_generated_grpc_stub_import_defaults_native_dns_resolver() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import os\n"
                "os.environ.pop('GRPC_DNS_RESOLVER', None)\n"
                "import rasa_sdk.grpc_py.action_webhook_pb2_grpc\n"
                "print(os.environ.get('GRPC_DNS_RESOLVER', ''))\n"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "native"
