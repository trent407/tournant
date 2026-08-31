"""Best-effort ESC/POS -> plain text extraction.

This does NOT need to be perfect: the physical kitchen ticket is produced
by forwarding the *raw* bytes to the real printer unmodified (see
printer_forward.py), so nothing in this module can affect what actually
prints. This only powers the live order log / dashboard, so it's safe to
keep tuning against real tickets once you've captured some from your
actual printer (mock_printer.py in sim/ saves raw jobs for exactly that).

Coverage here is deliberately conservative: known fixed-length commands are
skipped exactly; anything unrecognized just has its introducer byte(s)
skipped so we never lose printable text, at the cost of occasionally
leaving a stray byte or two in the output.
"""

from __future__ import annotations

ESC = 0x1B
GS = 0x1D
FS = 0x1C

# ESC <cmd> <n param bytes> -- commands with a fixed, known parameter count.
_ESC_FIXED = {
    ord("@"): 0,  # initialize
    ord("E"): 1,  # bold on/off
    ord("a"): 1,  # justification
    ord("!"): 1,  # select print mode
    ord("d"): 1,  # feed n lines
    ord("J"): 1,  # feed n dots
    ord("M"): 1,  # select font
    ord("R"): 1,  # select international char set
    ord("t"): 1,  # select code page
    ord("-"): 1,  # underline
    ord("{"): 1,  # upside-down
    ord("p"): 3,  # generate pulse (cash drawer kick)
}

# GS <cmd> <n param bytes> -- fixed-length GS commands.
_GS_FIXED = {
    ord("!"): 1,  # character size
    ord("B"): 1,  # white/black reverse
    ord("L"): 2,  # left margin
    ord("W"): 2,  # print area width
    ord("V"): 1,  # cut, m=0/1 form (full/partial, no extra param)
}


def extract_text(data: bytes) -> str:
    """Strip ESC/POS control sequences and return the printable text."""
    out: list[str] = []
    line: list[str] = []
    i = 0
    n = len(data)
    while i < n:
        b = data[i]

        if b == ESC and i + 1 < n:
            cmd = data[i + 1]
            if cmd == ord("V") and i + 2 < n and data[i + 2] in (0x41, 0x42):
                i += 4  # ESC V 'A'/'B' n -- feed-then-cut variant some drivers use
                continue
            nparams = _ESC_FIXED.get(cmd)
            if nparams is not None:
                i += 2 + nparams
            else:
                i += 2  # unknown ESC command: skip just the introducer, keep scanning
            continue

        if b == GS and i + 1 < n:
            cmd = data[i + 1]
            if cmd == ord("V") and i + 2 < n and data[i + 2] in (0x41, 0x42):
                i += 4  # GS V 'A'/'B' n -- feed-then-cut cut variant
                continue
            if cmd == ord("k"):  # barcode: variable length, ends before next control byte
                j = i + 2
                while j < n and data[j] not in (ESC, GS, FS):
                    j += 1
                i = j
                continue
            if cmd == 0x28:  # GS ( k -- 2D symbol (QR etc.), length-prefixed
                if i + 4 <= n:
                    plen = data[i + 2] | (data[i + 3] << 8)
                    i += 4 + plen
                else:
                    i += 2
                continue
            nparams = _GS_FIXED.get(cmd)
            if nparams is not None:
                i += 2 + nparams
            else:
                i += 2  # unknown GS command: skip just the introducer
            continue

        if b == FS and i + 1 < n:
            i += 2
            continue

        if b == 0x0A:  # LF
            out.append("".join(line))
            line = []
            i += 1
            continue
        if b == 0x0D:  # CR
            i += 1
            continue

        if b >= 0x20:
            # Printable ASCII kept as-is; extended/codepage bytes (>=0x80) are
            # kept too but not decoded -- accurate codepage mapping needs
            # tuning per printer/platform once you have real samples.
            line.append(chr(b))
        i += 1

    if line:
        out.append("".join(line))
    return "\n".join(s for s in out if s.strip())
