"""Stand-in for a delivery-app tablet: connects to a Tournant TCP source
listener and sends a canned ESC/POS order, the way a tablet's Bluetooth
print driver would send a job over RFCOMM. Use this against `mode: tcp`
sources in config.yaml for end-to-end testing without real Bluetooth
hardware.

Usage:
    python -m sim.mock_tablet --port 19001 --payload ubereats
    python -m sim.mock_tablet --port 19001 --payload doordash --chunked
"""

from __future__ import annotations

import argparse
import socket
import time

from sim.sample_payloads import (
    SAMPLE_CHOWNOW_ORDER,
    SAMPLE_DOORDASH_ORDER,
    SAMPLE_GRUBHUB_ORDER,
    SAMPLE_UBEREATS_ORDER,
)

PAYLOADS = {
    "ubereats": SAMPLE_UBEREATS_ORDER,
    "doordash": SAMPLE_DOORDASH_ORDER,
    "grubhub": SAMPLE_GRUBHUB_ORDER,
    "chownow": SAMPLE_CHOWNOW_ORDER,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--payload", choices=sorted(PAYLOADS), default="ubereats")
    parser.add_argument(
        "--chunked",
        action="store_true",
        help="dribble bytes out slowly, like a real BT link, to exercise idle-gap segmentation",
    )
    args = parser.parse_args()

    data = PAYLOADS[args.payload]
    with socket.create_connection((args.host, args.port)) as sock:
        if args.chunked:
            for i in range(0, len(data), 16):
                sock.sendall(data[i : i + 16])
                time.sleep(0.05)
        else:
            sock.sendall(data)
        print(f"[mock-tablet] sent {len(data)} bytes as '{args.payload}'")


if __name__ == "__main__":
    main()
