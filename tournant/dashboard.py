from __future__ import annotations

import html
import json
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Deque

from .models import Order


class OrderLog:
    """Thread-safe recent-orders buffer feeding the dashboard."""

    def __init__(self, maxlen: int = 200):
        self._orders: Deque[Order] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def add(self, order: Order) -> None:
        with self._lock:
            self._orders.appendleft(order)

    def recent(self) -> list[Order]:
        with self._lock:
            return list(self._orders)


def _make_handler(order_log: OrderLog):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # noqa: A002 - stdlib signature
            pass  # orchestrator logging already covers activity

        def do_GET(self):
            if self.path == "/api/orders":
                self._send_json(
                    [
                        {
                            "source": o.source,
                            "received_at": o.received_at.isoformat(),
                            "text": o.text,
                        }
                        for o in order_log.recent()
                    ]
                )
                return
            self._send_html()

        def _send_json(self, payload) -> None:
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self) -> None:
            rows = "".join(
                "<tr><td>{time}</td><td>{source}</td><td><pre>{text}</pre></td></tr>".format(
                    time=html.escape(o.received_at.strftime("%H:%M:%S")),
                    source=html.escape(o.source),
                    text=html.escape(o.text),
                )
                for o in order_log.recent()
            )
            body = (
                "<!doctype html><html><head><meta http-equiv=\"refresh\" content=\"5\">"
                "<title>Tournant</title></head><body>"
                "<h1>Tournant &mdash; recent orders</h1>"
                "<table border=\"1\" cellpadding=\"6\">"
                "<tr><th>Time</th><th>Source</th><th>Text</th></tr>"
                f"{rows}</table></body></html>"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def run_dashboard(order_log: OrderLog, host: str = "0.0.0.0", port: int = 8080) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), _make_handler(order_log))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
