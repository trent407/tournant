from __future__ import annotations

import socket


class Connection:
    """One accepted connection from a tablet (or, in sim mode, a mock tablet)."""

    def recv(self, bufsize: int = 4096) -> bytes:
        raise NotImplementedError

    def sendall(self, data: bytes) -> None:
        raise NotImplementedError

    def settimeout(self, seconds: float | None) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class SocketConnection(Connection):
    def __init__(self, sock: socket.socket, peer: str = ""):
        self._sock = sock
        self.peer = peer

    def recv(self, bufsize: int = 4096) -> bytes:
        return self._sock.recv(bufsize)

    def sendall(self, data: bytes) -> None:
        self._sock.sendall(data)

    def settimeout(self, seconds: float | None) -> None:
        self._sock.settimeout(seconds)

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass


class Listener:
    """Something that accepts one Connection at a time from a single source."""

    def accept(self) -> SocketConnection:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class TcpListener(Listener):
    """Plain-TCP stand-in for RfcommListener, used for local testing without
    Bluetooth hardware (see sim/mock_tablet.py)."""

    def __init__(self, host: str = "0.0.0.0", port: int = 0, backlog: int = 1):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((host, port))
        self._sock.listen(backlog)

    def accept(self) -> SocketConnection:
        client_sock, addr = self._sock.accept()
        return SocketConnection(client_sock, peer=f"{addr[0]}:{addr[1]}")

    def close(self) -> None:
        self._sock.close()


class RfcommListener(Listener):
    """Real Bluetooth Classic SPP listener. Linux/BlueZ only -- requires the
    adapter to already be configured (alias set, SDP SPP record registered
    on this channel) via scripts/setup_bluetooth.sh before a tablet can find
    and pair with it.
    """

    def __init__(self, channel: int = 1, backlog: int = 1):
        # AF_BLUETOOTH / BTPROTO_RFCOMM only exist on Linux; deliberately not
        # referenced at module import time so the rest of the codebase stays
        # importable (and testable) on machines without a Bluetooth stack.
        self._sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self._sock.bind(("", channel))
        self._sock.listen(backlog)
        self.channel = channel

    def accept(self) -> SocketConnection:
        client_sock, client_info = self._sock.accept()
        peer = client_info[0] if client_info else "unknown"
        return SocketConnection(client_sock, peer=peer)

    def close(self) -> None:
        self._sock.close()
