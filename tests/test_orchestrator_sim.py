import socket
import threading
import time

from sim.sample_payloads import SAMPLE_UBEREATS_ORDER
from tournant.models import Order
from tournant.orchestrator import Orchestrator, SourceConfig
from tournant.printer_forward import PrinterForwarder
from tournant.transport import TcpListener


class _CapturingPrinterServer:
    """Minimal TCP sink standing in for the real Epson TM-m30II printer."""

    def __init__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(1)
        self.port = self._sock.getsockname()[1]
        self.received: list[bytes] = []
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        conn, _ = self._sock.accept()
        with conn:
            self.received.append(conn.recv(65536))

    def close(self):
        self._sock.close()


def test_orchestrator_forwards_raw_bytes_and_emits_parsed_order():
    printer_server = _CapturingPrinterServer()
    printer = PrinterForwarder(host="127.0.0.1", port=printer_server.port)

    listener = TcpListener(host="127.0.0.1", port=0)
    actual_port = listener._sock.getsockname()[1]  # noqa: SLF001 - test needs the OS-assigned port

    captured_orders: list[Order] = []
    orch = Orchestrator(printer=printer, on_order=captured_orders.append)
    orch.add_source(SourceConfig(name="ubereats", listener=listener, idle_gap_seconds=0.2))
    orch.start()

    with socket.create_connection(("127.0.0.1", actual_port)) as tablet_sock:
        tablet_sock.sendall(SAMPLE_UBEREATS_ORDER)

    time.sleep(0.6)  # let idle-gap segmentation fire

    assert len(captured_orders) == 1
    order = captured_orders[0]
    assert order.source == "ubereats"
    assert "Cheeseburger" in order.text
    assert order.raw == SAMPLE_UBEREATS_ORDER

    time.sleep(0.2)
    assert printer_server.received == [SAMPLE_UBEREATS_ORDER]

    printer_server.close()
    orch.stop()
