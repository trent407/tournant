#!/usr/bin/env bash
# One-time-per-tablet Bluetooth setup on the Pi. Run this on-site while
# pairing ONE tablet at a time -- see docs/FIELD_SETUP.md for the full
# walkthrough and why this has to be done one tablet at a time.
#
# Usage: scripts/setup_bluetooth.sh "<Printer Bluetooth Name>" <rfcomm-channel>
set -euo pipefail

NAME="${1:?usage: setup_bluetooth.sh <printer-name> <channel>}"
CHANNEL="${2:?usage: setup_bluetooth.sh <printer-name> <channel>}"

echo "==> Powering on adapter and setting alias to: $NAME"
bluetoothctl <<EOF
power on
system-alias $NAME
discoverable on
pairable on
EOF

echo "==> Starting a persistent pairing agent (auto-accept, matching the real"
echo "    printer's Security: Low / passkey 0000 -- no PIN prompt on either side)"
if command -v bt-agent >/dev/null; then
    sudo pkill -f "bt-agent" >/dev/null 2>&1 || true
    sudo nohup bt-agent --capability=NoInputNoOutput -p 0000 >/tmp/bt-agent.log 2>&1 &
    disown
    echo "    bt-agent running in background (PID $!). This only lasts until reboot --"
    echo "    once everything's confirmed working, add it as its own systemd unit"
    echo "    (alongside systemd/tournant.service) so it survives a reboot."
else
    echo "bt-agent not found -- install it ('sudo apt install bluez-tools') for" >&2
    echo "auto-accept pairing; without it, pairing on the tablet may hang waiting" >&2
    echo "for a confirmation prompt the Pi never shows." >&2
fi

echo "==> Registering SPP service on RFCOMM channel $CHANNEL"
if command -v sdptool >/dev/null; then
    sudo sdptool add --channel="$CHANNEL" SP
else
    echo "sdptool not found -- install it (e.g. 'sudo apt install bluez-tools' or" >&2
    echo "'sudo apt install bluez' depending on your Pi OS release) and re-run." >&2
    exit 1
fi

echo "==> Done. Pi is now discoverable as '$NAME' and accepting SPP on channel $CHANNEL."
echo "    Now pair the ONE tablet you're onboarding to this name."
echo "    Once paired, the tablet remembers the Pi by MAC address, so you can"
echo "    safely re-run this script with a different name/channel for the next tablet."
