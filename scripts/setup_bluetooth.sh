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
