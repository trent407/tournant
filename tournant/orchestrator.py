from __future__ import annotations

import logging
import socket
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from .escpos import extract_text
from .models import Order
from .printer_forward import PrinterForwarder
from .transport import Listener

logger = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    name: str
    listener: Listener
    idle_gap_seconds: float = 0.75


class Orchestrator:
    """One background thread per source (tablet). Each thread accepts
    connections on its listener, and segments the byte stream into
    individual print jobs by idle-gap: many tablet print drivers hold the
    RFCOMM link open between orders rather than reconnecting each time, so
    "the sender went quiet for `idle_gap_seconds`" is a more robust job
    boundary than trying to recognize every ESC/POS cut-command variant.

    Every job is forwarded to the real printer byte-for-byte before
    anything else happens to it, so a parsing bug can never affect what
    prints in the kitchen.
    """

    def __init__(self, printer: PrinterForwarder, on_order: Optional[Callable[[Order], None]] = None):
        self.printer = printer
        self.on_order = on_order or (lambda order: None)
        self._threads: list[threading.Thread] = []
        self._stop = threading.Event()

    def add_source(self, source: SourceConfig) -> None:
        t = threading.Thread(target=self._run_source, args=(source,), daemon=True, name=f"tournant-{source.name}")
        self._threads.append(t)

    def start(self) -> None:
        for t in self._threads:
            t.start()

    def stop(self) -> None:
        self._stop.set()
        for t in self._threads:
            t.join(timeout=2)

    def join(self) -> None:
        for t in self._threads:
            t.join()

    def _run_source(self, source: SourceConfig) -> None:
        logger.info("%s: listening", source.name)
        while not self._stop.is_set():
            try:
                conn = source.listener.accept()
            except OSError:
                if self._stop.is_set():
                    return
                raise
            logger.info("%s: connected (%s)", source.name, conn.peer)
            try:
                self._handle_connection(source, conn)
            finally:
                conn.close()

    def _handle_connection(self, source: SourceConfig, conn) -> None:
        conn.settimeout(source.idle_gap_seconds)
        buf = bytearray()
        while not self._stop.is_set():
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                if buf:
                    self._emit(source, bytes(buf))
                    buf.clear()
                continue
            if not chunk:
                break
            buf.extend(chunk)
        if buf:
            self._emit(source, bytes(buf))

    def _emit(self, source: SourceConfig, raw: bytes) -> None:
        logger.info("%s: captured %d bytes, forwarding to printer", source.name, len(raw))
        try:
            self.printer.send(raw)
        except OSError:
            logger.exception("%s: failed to forward job to printer", source.name)

        order = Order(
            source=source.name,
            received_at=datetime.now(timezone.utc),
            raw=raw,
            text=extract_text(raw),
        )
        try:
            self.on_order(order)
        except Exception:
            logger.exception("%s: on_order callback failed", source.name)
