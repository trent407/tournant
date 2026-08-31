from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class PrinterConfig:
    host: str
    port: int = 9100


@dataclass
class DashboardConfig:
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass
class SourceSpec:
    name: str
    mode: str  # "bluetooth" | "tcp" (tcp is for the simulator)
    channel: Optional[int] = None  # bluetooth mode
    host: str = "0.0.0.0"  # tcp mode
    port: Optional[int] = None  # tcp mode
    idle_gap_seconds: float = 0.75


@dataclass
class TournantConfig:
    printer: PrinterConfig
    sources: list[SourceSpec]
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)


def load_config(path: str | Path) -> TournantConfig:
    data = yaml.safe_load(Path(path).read_text())

    printer = PrinterConfig(**data["printer"])
    dashboard = DashboardConfig(**data.get("dashboard", {}))
    sources = [SourceSpec(**s) for s in data["sources"]]

    for s in sources:
        if s.mode not in ("bluetooth", "tcp"):
            raise ValueError(f"source '{s.name}': mode must be 'bluetooth' or 'tcp', got {s.mode!r}")
        if s.mode == "bluetooth" and s.channel is None:
            raise ValueError(f"source '{s.name}': mode=bluetooth requires 'channel'")
        if s.mode == "tcp" and s.port is None:
            raise ValueError(f"source '{s.name}': mode=tcp requires 'port'")

    return TournantConfig(printer=printer, sources=sources, dashboard=dashboard)
