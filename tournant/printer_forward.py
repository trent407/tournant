from __future__ import annotations

import socket


class PrinterForwarder:
    """Sends a raw ESC/POS job to the real printer's Ethernet raw/JetDirect
    interface (Star printers, like most receipt printers, accept a raw
    byte stream on TCP port 9100 -- no protocol wrapping needed).
    """

    def __init__(self, host: str, port: int = 9100, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, data: bytes) -> None:
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.sendall(data)
