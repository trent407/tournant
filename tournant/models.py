from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Order:
    """One intercepted print job, decoded on a best-effort basis.

    `raw` is always the exact, untouched bytes the tablet sent -- that's
    what gets forwarded to the real printer, so it's authoritative
    regardless of how well `text` was parsed.
    """

    source: str
    received_at: datetime
    raw: bytes
    text: str
