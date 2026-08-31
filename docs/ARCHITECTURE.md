# Architecture

## What this is

Tournant sits between the delivery-platform tablets and the kitchen's
Epson TM-m30II printer. Instead of each tablet's Bluetooth print driver
talking directly to the printer, it talks to a Raspberry Pi impersonating
the printer over Bluetooth Classic SPP (Serial Port Profile). The Pi:

1. accepts the print job (raw ESC/POS bytes) from the tablet,
2. immediately forwards those exact bytes, unmodified, to the real
   printer over Ethernet (raw/JetDirect on TCP port 9100), and
3. separately, best-effort decodes the bytes into readable text for a
   live dashboard / order log.

Step 2 and step 3 are independent. **Step 2 has no dependency on step 3's
parsing being correct.** This is the key design decision: the thing that
must not break (a ticket printing correctly in the kitchen) does not
depend on the thing that's hardest to get exactly right (interpreting an
undocumented, vendor-specific ESC/POS dialect). Even a badly-parsed or
completely unparseable job still prints fine.

## Why Bluetooth impersonation works here

Epson's Bluetooth-capable TM-series printers (this kitchen's is a
TM-m30II) expose themselves over Bluetooth Classic as a plain SPP RFCOMM
endpoint -- the same interface Epson's own documentation confirms only
holds **one connected device at a time**, which is exactly the "DoorDash
and Uber Eats fight for control" symptom observed on-site. The tablet's
print driver just streams raw ESC/POS bytes down that serial pipe --
there's no authentication or cryptographic binding tying a pairing to a
specific physical printer (Bluetooth security is set to Epson's default
"Middle" level, which doesn't change this). Whatever device the tablet is
paired with under the expected name/MAC receives the job. That means a
device that presents the same SPP service (right device name during
pairing, then remembered by MAC afterward) is indistinguishable to the
tablet from the real printer -- and unlike the real printer's firmware,
the Pi *can* hold several such connections at once, which is what
actually fixes the contention rather than just relocating it.

Epson's TM printers also confirm raw ESC/POS over TCP port 9100 as a
standard interface (in addition to their ePOS-Print XML/HTTP mode, which
Tournant doesn't use), matching what `printer_forward.py` already does
and what the on-site `nc -zv <printer-ip> 9100` test confirmed reachable.

## Component map

- `tournant/transport.py` -- `Listener`/`Connection` abstraction with two
  implementations: `RfcommListener` (real Bluetooth, Linux/BlueZ, used on
  the Pi) and `TcpListener` (plain TCP, used by the simulator so the rest
  of the stack is testable without any Bluetooth hardware).
- `tournant/orchestrator.py` -- one thread per tablet/source. Segments
  the byte stream into individual jobs by idle-gap (see below), forwards
  each job to the printer, then hands it off for parsing/logging.
- `tournant/escpos.py` -- best-effort ESC/POS -> text decoder. Tune this
  against real captured tickets; it can never make printing worse.
- `tournant/printer_forward.py` -- opens a TCP connection to the real
  printer and sends raw bytes. This is the only thing that touches the
  physical printer.
- `tournant/dashboard.py` -- minimal stdlib HTTP server (no extra
  dependencies) showing recent orders, auto-refreshing.
- `tournant/cli.py` / `tournant/config.py` -- wiring: reads
  `config.yaml`, builds one source per tablet, starts everything.
- `sim/` -- `mock_tablet.py` (stands in for a tablet's BT print driver,
  over plain TCP) and `mock_printer.py` (stands in for the real printer's
  raw/9100 interface, and saves every job it receives to `captures/` so
  you can diff real captured tickets against what the parser produces).

## Job boundaries: idle-gap segmentation

Rather than trying to recognize every ESC/POS "cut" command variant
(there are several: `GS V 0`, `GS V 1`, `GS V 'A' n`, `GS V 'B' n`, and
some Star-specific ones) to know where one order ends and the next
begins, the orchestrator segments purely on **timing**: once a source
goes quiet for `idle_gap_seconds` (default 0.75s, configurable per
source), whatever has been buffered is treated as one complete job. This
matches how most tablet print drivers behave in practice -- they hold the
RFCOMM connection open across multiple orders and only pause between
jobs -- and it's robust to command variants we haven't seen yet. If
real-world testing shows jobs getting split or merged incorrectly, this
is the first knob to adjust (`idle_gap_seconds` in `config.yaml`).

## Multiple tablets, one Bluetooth adapter

A single Bluetooth Classic adapter can register several independent SPP
services on different RFCOMM channels and hold several simultaneous
connections. Each tablet gets its own channel (see
`config/config.example.yaml`). The one constraint is that the adapter
only advertises one name at a time during discovery -- see
`docs/FIELD_SETUP.md` for how that's handled when pairing four different
tablets that may each expect a differently-named printer.
