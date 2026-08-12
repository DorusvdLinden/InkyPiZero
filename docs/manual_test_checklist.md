# Manual test checklist: 2026-08-12/13 fixes

A step-by-step checklist for a **human** to run against the real, deployed
Pi - covers everything from the `todo-fonts-wifi-fixes` session (now
merged to `main`) that the automated regression suite
(`scripts/test_*.py`, see [development.md](./development.md)) can't check
on its own: physical button presses, real e-paper appearance, actual WiFi
AP behavior, and phone-camera QR scanning. Run the automated suite first
if you haven't already (`python scripts/test_locations.py` etc.) - this
checklist assumes that already passed and is testing the things it
can't reach.

**Prerequisites**:
- SSH access to the Pi (`ssh -i ~/.ssh/id_rsa_raspberrypi
  dorus@192.168.1.224`, or your current IP if it's changed)
- Physical access to the panel and its buttons
- A phone with a camera app, for the QR code check
- A second WiFi network you can temporarily switch the Pi to (or a phone
  hotspot), for the SSID rename and reconnect-check items
- Confirm the Pi is on `main` and up to date: `cd ~/InkyPiZero && git
  status` should show `On branch main`, clean, `up to date with
  'origin/main'`

Check off each box as you go. If anything doesn't match "Expected", stop
and report it rather than continuing - note which step failed and what
you saw instead.

---

## 1. Shutdown-screen saturation fix

**What changed**: `button_listener.py`'s blank-before-shutdown screen now
renders at your actually-configured `inky_saturation` (default `0.0`)
instead of a hardcoded `0.5`.

1. [ ] Note the panel's current image (anything already displayed).
2. [ ] Press **button A** on the back of the display.
3. [ ] Watch the panel blank, then the Pi should power off (you'll need
   to power it back on via the physical power connector to continue
   testing - or skip the actual power-off by testing via the web UI's
   `/shutdown` route instead, which calls the same code path).

**Expected**: the panel goes fully white/blank, matching the same flat
color you'd see on a normal render's background (not a visibly different
shade than usual).

4. [ ] **Also check for the known, separately-tracked issue**: look
   closely at the blank screen for a faint sprinkling of black dots. This
   was investigated (`TODO.md`) and is believed to be a physical e-paper
   ghosting artifact, not a software bug - if you still see it, that's
   expected and already documented, not a regression. If it's gone
   entirely, that's worth reporting - it would mean the hypothesis was
   wrong.

---

## 2. Chart gridline label collision fix

**What changed**: in **gridlines** screen mode, a tick label right next
to the topmost/bottommost temperature line no longer overlaps it.

1. [ ] Switch to gridlines mode (**button C**, or confirm it's already
   active - it's the default).
2. [ ] Force a render: `sudo systemctl start pi-weather-display.service`
   on the Pi (or wait for the next 10-minute tick).
3. [ ] Look at the chart's left-side temperature axis labels (e.g. "10°",
   "20°"), specifically near the top/bottom of the temperature line's own
   range.

**Expected**: no axis label visually overlaps/touches the day's actual
max/min temperature label. This is weather-dependent - if today's data
doesn't happen to produce a near-collision, this step can't show much;
the fix was verified against a crafted repro case in the automated suite,
this is just a real-hardware sanity check, not the primary verification.

---

## 3. Font glyph fallback + location name translation

**What changed**: the header's location name now shows in English
outside the Netherlands (was previously Dutch, silently falling back to
local script - e.g. Japanese - when no Dutch translation existed). The
underlying glyph-fallback mechanism (a bundled Noto Sans JP font) still
exists as a safety net for the rarer case where even English isn't
available.

Since your Pi's real configured location is inside the Netherlands
(`config.py`'s default, Sittard), this can't be observed on the live
panel without a temporary config change:

1. [ ] Via the web UI (`http://<pi-ip>:8080/settings`) or by editing
   `config.py` directly, temporarily set `latitude`/`longitude` to a
   non-Netherlands location - e.g. Tokyo: `35.6762, 139.6503`.
2. [ ] Force a render.
3. [ ] Check the header (top-left, next to the date).

**Expected**: reads something like "Donderdag 13 augustus, Suginami,
Japan" - an English place name, not Japanese characters, and not blank.

4. [ ] **Restore your real location** afterward (undo the settings
   change, or force another render after reverting `config.py`).

---

## 4. WiFi: SSID rename

**What changed**: editing a saved network can now rename its SSID (not
just its password), via `/wifi`'s edit form.

1. [ ] Go to `http://<pi-ip>:8080/wifi`.
2. [ ] Pick a saved (non-active, to be safe) network's "Edit" option.
3. [ ] Enter a value in the new "nieuwe SSID" field - e.g. a harmless
   typo-of-itself variant of a test network's real name.
4. [ ] Submit.
5. [ ] Confirm the network list now shows the new name.
6. [ ] SSH in and confirm at the OS level: `nmcli connection show` should
   list the renamed profile with matching `NAME` and no leftover
   duplicate old-named profile.
7. [ ] Rename it back to its original SSID afterward, same flow.

**Expected**: one connection profile, renamed in place - no remove+re-add,
no duplicate profile.

---

## 5. WiFi: periodic reconnect check

**What changed**: `pi-weather-web.service` now re-checks connectivity
every 60s in the background, and falls back to the setup AP after 3
consecutive failures (not just once, at service startup, like before).

This is the slowest check in this list (needs ~3+ minutes of induced
disconnection) and is somewhat disruptive - **do this one last**, and
only if you're prepared for the Pi to briefly host its own setup AP.

1. [ ] Confirm the Pi is connected to your real network normally.
2. [ ] Disconnect it from WiFi at the router/AP side (e.g. temporarily
   block its MAC address, or change the router's password so the Pi's
   saved credentials stop working) - not from the Pi itself, to simulate
   a real "router went away" scenario.
3. [ ] Wait roughly 3-4 minutes (3 consecutive 60s-spaced failed checks).
4. [ ] Check `journalctl -u pi-weather-web.service` for reconnect-check
   log lines, and check whether the panel now shows the setup-AP screen
   (SSID/password/QR code).

**Expected**: after ~3 minutes of being unreachable, the Pi falls back to
hosting its own setup AP and the panel shows the setup screen -
previously this only happened if the service was restarted while
disconnected, never automatically at runtime.

5. [ ] Restore normal network access (undo step 2) and confirm the Pi
   reconnects to your real network again (may need a manual reconnect
   via `/wifi`, or power-cycling, depending on how AP mode was entered).

---

## 6. WiFi: captive-portal DNS redirect

**What changed**: while the Pi is hosting its setup AP, any domain name
now resolves to the Pi's own IP (wildcard DNS), so opening any plain
`http://` URL lands on the setup page.

1. [ ] Get the Pi into setup-AP mode (via step 5 above, or by taking it
   out of range of any known network).
2. [ ] Join the AP from a phone or laptop using the SSID/password shown
   on the panel.
3. [ ] Open a browser and navigate to any arbitrary plain-HTTP address,
   e.g. `http://example.com` (**not** `https://` - HTTPS will fail TLS
   validation against the Pi's bare IP, this is expected, see
   `docs/networking.md`).

**Expected**: lands on the Pi's setup/WiFi-provisioning page, without
needing to type `http://192.168.4.1` directly.

---

## 7. WiFi: QR code on the setup screen

**What changed**: the setup screen now shows a WiFi QR code alongside the
existing text instructions, for one-tap phone joining.

1. [ ] With the Pi in setup-AP mode (panel showing the setup screen),
   open your phone's native camera app (not a dedicated QR scanner app -
   the point is that this should work with the default camera).
2. [ ] Point it at the QR code shown on the panel.

**Expected**: the phone recognizes it as a WiFi network and offers to
join - confirm it actually connects successfully, not just that the code
scans as *some* WiFi network. This is the one item in this whole
checklist that has **never been tested with a real phone** before - the
implementation only computed/simulated the module size as "should be
scannable," so this step is the first real confirmation either way.

---

## Wrap-up

- [ ] Restore `config.py`/settings to your real values if you changed
  anything during testing (location, WiFi networks).
- [ ] Confirm a final normal render looks right:
  `sudo systemctl start pi-weather-display.service`, check the panel
  shows your real location/weather correctly.
- [ ] Report back which items passed/failed - see `TODO.md` for where any
  new finding should be logged.
