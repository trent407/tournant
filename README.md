# Tournant

A Raspberry Pi 4 that sits in the kitchen impersonating the printer over
Bluetooth SPP, so it can capture orders from multiple delivery-app tablets
(Uber Eats, DoorDash, GrubHub, ChowNow) and re-forward each one, byte for
byte, to the real Star Micronics printer over Ethernet -- while also
logging a best-effort readable copy of each order to a live dashboard.

See `docs/ARCHITECTURE.md` for how and why this works, and
`docs/FIELD_SETUP.md` for the on-site walkthrough (pairing tablets,
finding the printer's Bluetooth name/IP, rollback plan).

**Status:** core logic is written and unit/integration tested against a
simulator (no physical hardware involved yet). Bluetooth pairing and
real-printer forwarding still need on-site verification -- that's what
`docs/FIELD_SETUP.md` walks through.

## Design principle

The physical kitchen ticket is produced by forwarding the tablet's raw
bytes to the real printer **unmodified**. Nothing about order parsing
(which is inherently best-effort against an undocumented per-platform
ESC/POS dialect) can affect what actually prints. Parsing only feeds the
dashboard, and can be tuned safely after the fact using real captured
tickets.

## Try it tonight (no hardware needed)

This exercises the full pipeline -- tablet print driver -> Tournant ->
real printer -- using TCP stand-ins for both ends, so you can confirm the
logic before you're on-site tomorrow.

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest   # unit + integration tests, no hardware required
```

Or run it live, three terminals:

```
# 1. stand-in for the real printer
python -m sim.mock_printer --port 19100

# 2. Tournant itself, pointed at the fake printer, with tcp-mode sources
cp config/config.example.yaml config/config.yaml
# edit config/config.yaml: comment out the `bluetooth` sources block,
# uncomment the `tcp` sources block, set printer.port to 19100
python -m tournant.cli --config config/config.yaml -v

# 3. stand-in for a tablet sending an order
python -m sim.mock_tablet --port 19001 --payload ubereats
```

Then open `http://localhost:8080` to see the decoded order on the
dashboard, and check `captures/` (created by mock_printer) to confirm the
exact bytes that would have gone to the real printer.

## Run it for real (on the Pi, in the kitchen)

See `docs/FIELD_SETUP.md` -- covers finding the printer's Bluetooth name
and IP, pairing each tablet one at a time, rollback if something doesn't
work, and making it persistent via systemd.

## Layout

```
tournant/           core package (transport, orchestrator, parser, dashboard, cli)
sim/                mock tablet + mock printer for hardware-free testing
tests/              pytest suite
config/             config.example.yaml (copy to config.yaml, gitignored)
scripts/            setup_bluetooth.sh -- on-site adapter/pairing setup
systemd/            tournant.service -- run on boot
docs/               ARCHITECTURE.md, FIELD_SETUP.md
```

## Known unknowns (confirm on-site, see docs/FIELD_SETUP.md)

- Exact printer model/name/MAC/IP.
- Whether DoorDash/GrubHub/ChowNow tablets currently print via Bluetooth
  at all, or only display orders on-screen.
- Whether one Bluetooth adapter reliably holds 4 simultaneous RFCOMM
  connections, or whether a second (USB) adapter is needed.
- iOS (GrubHub iPad) Bluetooth SPP behavior may differ from Android and
  needs its own verification.
