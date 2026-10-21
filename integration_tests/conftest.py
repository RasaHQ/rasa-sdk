from pathlib import Path

_CERTS_DIR = Path(__file__).parent / "grpc_server" / "setup" / "certs"


def _read_pem(filename: str) -> bytes:
    """Read a PEM fixture used by the gRPC TLS tests."""
    return (_CERTS_DIR / filename).read_bytes()


def ca_cert() -> bytes:
    """Return a test CA certificate."""
    return _read_pem("ca.pem")


def client_key() -> bytes:
    """Return a test client key."""
    return _read_pem("client-key.pem")


def client_cert() -> bytes:
    """Return a test client certificate."""
    return _read_pem("client.pem")


def server_cert() -> bytes:
    """Return a test server certificate."""
    return _read_pem("server.pem")


def server_cert_key() -> bytes:
    """Return a test server key."""
    return _read_pem("server-key.pem")
