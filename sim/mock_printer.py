"""Stand-in for the real Epson TM-m30II printer: listens on a TCP port the same way
the printer's raw/JetDirect interface does (port 9100), and just logs and
saves whatever it receives. Point PrinterForwarder (via config.yaml's
`printer.host`/`printer.port`) at this during local testing so you can
confirm the exact bytes a tablet sent reach "the printer" unmodified.

Usage:
    python -m sim.mock_printer --port 19100
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import socketserver


class _Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        data = self.request.recv(65536)
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        out_dir = pathlib.Path(self.server.capture_dir)  # type: ignore[attr-defined]
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"job-{ts}.bin"
        path.write_bytes(data)
        print(f"[mock-printer] received {len(data)} bytes from {self.client_address}, saved to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=19100)
    parser.add_argument("--capture-dir", default="captures")
    args = parser.parse_args()

    server = socketserver.ThreadingTCPServer((args.host, args.port), _Handler)
    server.capture_dir = args.capture_dir  # type: ignore[attr-defined]
    print(f"[mock-printer] listening on {args.host}:{args.port}, saving jobs to {args.capture_dir}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
