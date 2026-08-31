from __future__ import annotations

import argparse
import logging

from .config import SourceSpec, TournantConfig, load_config
from .dashboard import OrderLog, run_dashboard
from .orchestrator import Orchestrator, SourceConfig
from .printer_forward import PrinterForwarder
from .transport import Listener, RfcommListener, TcpListener

logger = logging.getLogger(__name__)


def _build_listener(spec: SourceSpec) -> Listener:
    if spec.mode == "bluetooth":
        return RfcommListener(channel=spec.channel)  # type: ignore[arg-type]
    return TcpListener(host=spec.host, port=spec.port)  # type: ignore[arg-type]


def run(config: TournantConfig) -> None:
    printer = PrinterForwarder(host=config.printer.host, port=config.printer.port)
    order_log = OrderLog()
    run_dashboard(order_log, host=config.dashboard.host, port=config.dashboard.port)

    orch = Orchestrator(printer=printer, on_order=order_log.add)
    for spec in config.sources:
        listener = _build_listener(spec)
        orch.add_source(SourceConfig(name=spec.name, listener=listener, idle_gap_seconds=spec.idle_gap_seconds))

    orch.start()
    logger.info(
        "tournant running with %d source(s); dashboard on %s:%s",
        len(config.sources),
        config.dashboard.host,
        config.dashboard.port,
    )
    orch.join()


def main() -> None:
    parser = argparse.ArgumentParser(description="Tournant: kitchen order interceptor")
    parser.add_argument("--config", required=True, help="path to config.yaml")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config(args.config)
    run(config)


if __name__ == "__main__":
    main()
