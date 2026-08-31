"""Hand-built ESC/POS byte sequences that look like real delivery-app order
tickets, for testing without physical hardware. Replace/extend these with
bytes captured from your actual printer once you have on-site access --
mock_printer.py saves every job it receives to captures/*.bin for exactly
that purpose (see docs/FIELD_SETUP.md).
"""

ESC = b"\x1b"
GS = b"\x1d"


def _text(s: str) -> bytes:
    return s.encode("ascii", errors="replace") + b"\n"


SAMPLE_UBEREATS_ORDER = (
    ESC
    + b"@"  # initialize
    + ESC
    + b"!"
    + b"\x38"  # bold + double size
    + _text("UBER EATS")
    + ESC
    + b"!"
    + b"\x00"  # normal mode
    + _text("Order #A1B2C3")
    + _text("------------------------")
    + _text("1x Cheeseburger")
    + _text("  - No onions")
    + _text("2x Fries (Large)")
    + _text("------------------------")
    + _text("Total: $24.50")
    + GS
    + b"V"
    + b"\x00"  # full cut
)

SAMPLE_DOORDASH_ORDER = (
    ESC
    + b"@"
    + _text("DOORDASH")
    + _text("Order #DD-9981")
    + _text("1x Veggie Bowl")
    + _text("Total: $14.25")
    + GS
    + b"V"
    + b"\x00"
)

SAMPLE_GRUBHUB_ORDER = (
    ESC
    + b"@"
    + _text("GRUBHUB")
    + _text("Order #GH-4471")
    + _text("3x Chicken Tacos")
    + _text("Total: $19.00")
    + GS
    + b"V"
    + b"\x00"
)

SAMPLE_CHOWNOW_ORDER = (
    ESC
    + b"@"
    + _text("CHOWNOW")
    + _text("Order #CN-1187")
    + _text("1x Pad Thai")
    + _text("Total: $16.75")
    + GS
    + b"V"
    + b"\x00"
)
