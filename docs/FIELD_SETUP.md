# On-site setup walkthrough

This assumes you've already run the simulator at least once (see
README.md's "Try it tonight") so you know the software itself works.
Everything below is about getting real hardware talking to it.

**Do this during a slow period, not mid-rush**, and don't touch anything
until you've confirmed the rollback step works. Nothing here should take
down order printing for more than a few minutes per tablet if you follow
the order below.

## 0. Bring

- Raspberry Pi 4 (2GB is fine for this workload), power supply, case.
- Ethernet cable long enough to reach the same switch/router the printer
  and POS are on.
- A laptop for SSH access to the Pi (or a spare monitor+keyboard).
- Optionally, a USB Bluetooth adapter as a spare/backup if the Pi's
  onboard adapter turns out to be flaky with 4 simultaneous connections.

## 1. Identify the printer's real identity -- CONFIRMED

The printer is an **Epson TM-m30II** (serial X855023961). Read off the
config sheet (self-test page: hold Feed while powering on):

- **Bluetooth device name:** `TM-m30II_023961`
- **BD_ADDR (Bluetooth MAC):** `00:01:90:61:42:64`
- **Passkey:** `0000`, **Security: Low** -- effectively no real pairing
  authentication. The Pi's Bluetooth agent should auto-accept pairing
  (see step 4) rather than prompt for confirmation, matching this.
- **Mode: Auto re-connect enable** -- the printer actively tries to
  reclaim connections from devices it's previously paired with. Power it
  off or move it out of range during the Pi's first pairing test (step
  4) so it can't race the Pi for a tablet's connection.
- **Ethernet MAC:** `38-1A-52-9B-56-73` -- worth pinning to a DHCP
  reservation for `192.168.1.50` on the router so the IP never drifts.
- The self-test sheet's own Ethernet IP field showed "(None)" -- that's
  the static-config field, not the live DHCP lease; the confirmed
  working IP is `192.168.1.50` (already set in `config/config.yaml`).

## 2. Confirm the printer's raw/9100 port works

From your laptop, on the same network:

```
printf '\x1b@Test\n\x1dV\x00' | nc <printer-ip> 9100
```

If a small test slip prints, `printer_forward.py`'s approach (raw bytes
over TCP 9100) is confirmed working against your actual printer before
you touch any tablets.

## 3. Set up the Pi

```
sudo apt update && sudo apt install -y python3-pip bluez bluez-tools git
git clone <this repo's URL> tournant
cd tournant
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml
# edit config/config.yaml: set printer.host to the IP from step 1
```

## 4. Onboard ONE tablet at a time

This is the part that requires the adapter to briefly advertise under
the real printer's name, so do it one platform at a time rather than all
four at once.

1. On the tablet you're onboarding (start with whichever platform is
   least busy right now), open its printer/Bluetooth settings and
   **forget/unpair the real printer**. Power the real printer's
   Bluetooth off or move it out of range for this step -- it's set to
   "Auto re-connect enable" (step 1), so leaving it live risks it
   racing the Pi to reclaim the tablet's connection.
2. On the Pi:
   ```
   ./scripts/setup_bluetooth.sh "TM-m30II_023961" 1
   ```
   (use channel `1` for the first tablet, `2` for the second, etc. --
   matches `config/config.yaml`'s `sources[].channel`. The script also
   sets the Pi's Bluetooth agent to auto-accept pairing, matching the
   real printer's Security: Low / passkey 0000 -- no PIN prompt should
   appear on either side.)
3. On the tablet, scan for Bluetooth printers and pair with the name
   from step 1 -- it'll now find the Pi.
4. Start Tournant on the Pi (see README's "Run it for real"), then
   trigger a test print from the tablet's app (most delivery apps have a
   "test print" option in printer settings; otherwise wait for a real
   order).
5. **Confirm the physical ticket printed correctly** and matches what
   printed before you started. Check the Tournant dashboard
   (`http://<pi-ip>:8080`) shows the order with roughly the right text --
   don't worry yet if formatting looks slightly off, that only affects
   the dashboard, not the ticket.

### Rollback if step 4/5 fails

Unpair the tablet from the Pi, power the real printer's Bluetooth back
on, re-pair the tablet directly to the printer's original name. You're
back to exactly the original setup. Nothing about the printer itself was
modified at any point.

## 5. Repeat for the remaining 3 tablets

Same steps, incrementing the channel number each time
(`setup_bluetooth.sh "<name>" 2`, `3`, `4`). Each tablet remembers the Pi
by MAC address after pairing, so re-running `setup_bluetooth.sh` with a
different name for the next tablet does not break tablets already
onboarded.

**Before starting this for platforms other than Uber Eats**, confirm on
that tablet whether it's actually printing via Bluetooth to a printer at
all today, or just displaying orders on-screen -- the Uber Eats
Bluetooth-to-this-printer relationship is confirmed, but DoorDash/GrubHub/
ChowNow's current setup wasn't, as of when this was written. If a
platform doesn't print via Bluetooth today, onboarding it here just means
it'll start printing to the shared printer (still useful), but there's no
existing pairing to "take over" -- you're setting up printing from
scratch for that one.

## 6. Make it persistent

Once all tablets are confirmed working:

```
sudo cp systemd/tournant.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tournant.service
```

(Edit the `User=`/paths in `systemd/tournant.service` first if your Pi
user or clone path differs from `pi`/`/home/pi/tournant`.)

## 7. Capture real tickets to tune the parser

`sim/mock_printer.py` isn't needed on-site (the real printer is now in
the loop), but every job Tournant handles is available via
`http://<pi-ip>:8080/api/orders` as JSON, and the dashboard shows the
best-effort decoded text. If a platform's text looks garbled, that's a
`tournant/escpos.py` tuning problem, not a printing problem -- the ticket
already printed correctly by the time you're looking at the dashboard.
