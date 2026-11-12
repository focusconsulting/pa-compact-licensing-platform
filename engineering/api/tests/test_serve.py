import socket
import ssl
import stat
import threading
from pathlib import Path

import pytest

from licensing_api import serve


def test_a_client_trusting_only_the_certificate_completes_a_handshake_with_localhost(
    tmp_path: Path,
):
    cert_path, key_path = serve.write_certificate(tmp_path / 'tls')
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(cert_path, key_path)
    listener = socket.create_server(('127.0.0.1', 0))
    port = listener.getsockname()[1]

    def accept_one() -> None:
        connection, _ = listener.accept()
        with server_context.wrap_socket(connection, server_side=True) as tls:
            tls.recv(1)

    server = threading.Thread(target=accept_one)
    server.start()
    try:
        # The context the container's health check builds (ecs.tf).
        client_context = ssl.create_default_context(cafile=str(cert_path))
        with (
            socket.create_connection(('127.0.0.1', port)) as raw,
            client_context.wrap_socket(raw, server_hostname='localhost') as tls,
        ):
            assert tls.version() == 'TLSv1.3'
            tls.sendall(b'x')
    finally:
        server.join(timeout=5)
        listener.close()


def test_the_private_key_is_readable_only_by_its_owner(tmp_path: Path):
    _, key_path = serve.write_certificate(tmp_path / 'tls')

    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(key_path.parent.stat().st_mode) == 0o700


def test_each_start_makes_a_new_key(tmp_path: Path):
    _, first = serve.write_certificate(tmp_path / 'tls')
    first_key = first.read_bytes()
    _, second = serve.write_certificate(tmp_path / 'tls')

    assert second.read_bytes() != first_key


def test_main_hands_the_process_to_gunicorn_with_the_new_certificate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    executed: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(serve, 'TLS_DIR', tmp_path / 'tls')
    monkeypatch.setattr(serve.os, 'execvp', lambda file, args: executed.append((file, args)))

    serve.main()

    [(file, args)] = executed
    assert file == 'gunicorn'
    assert args[-1] == 'licensing_api.__main__:app'
    assert args[args.index('--bind') + 1] == '0.0.0.0:8000'
    assert args[args.index('--worker-tmp-dir') + 1] == '/dev/shm'
    assert '--no-control-socket' in args
    cert_path = Path(args[args.index('--certfile') + 1])
    key_path = Path(args[args.index('--keyfile') + 1])
    ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(cert_path, key_path)
