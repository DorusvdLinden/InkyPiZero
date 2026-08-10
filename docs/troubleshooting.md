# Troubleshooting

## Timer/service not running

Check whether the timer is active:
```bash
systemctl status pi-weather-display.timer
```
This should show `Active: active (waiting)` (it's a timer, so it's normally
"waiting" between runs, not continuously "running").

Check the most recent run of the render itself:
```bash
systemctl status pi-weather-display.service
```

### Render crashes referencing a function/attribute that isn't actually in the source

If `journalctl -u pi-weather-display.service` shows an `AttributeError`/
`ImportError` naming something that clearly isn't in the current
`git log`'d source (e.g. a function you already deleted in your last
commit), suspect a **stale compiled bytecode cache**, not a real bug -
seen once on 2026-08-10 right after a Pi reboot + `git pull`: `layout.py`'s
`__pycache__/*.pyc` correctly recompiled from the freshly-pulled source,
but `canvas.py`'s didn't, despite both files updating in the same pull
(confirmed by comparing `ls -la --time-style=full-iso` on the `.py` vs
`.pyc` - the source's mtime was newer, but the stale `.pyc` was used
anyway). Root cause not fully pinned down; the fix is simple and safe
either way (`__pycache__/` is gitignored, purely regenerable):
```bash
sudo find /home/dorus/InkyPiZero -name '__pycache__' -type d -exec rm -rf {} +
sudo systemctl start pi-weather-display.service
```

## Display isn't updating every 10 minutes / seems "stuck"

This is expected, not a bug - see `docs/settings.md`'s "Display refresh
cadence" section. `main.py` still fetches fresh data every 10 minutes,
but only pushes to the physical panel when the current icon/temperature
changed, or at least once an hour regardless. Check the actual timer
runs are happening (this doesn't mean the *display* updated, just that
the check ran):
```bash
journalctl -u pi-weather-display.service -n 50
```
A skipped tick logs `Skipping display update - icon/temp unchanged and
last refresh was under an hour ago` and exits cleanly - that's working
as designed, not a failure. Check the current freshness state directly:
```bash
cat /var/lib/pi-weather-display/display_freshness.json
```
To force an immediate real refresh regardless of state, either press any
screen-mode button, save any setting in the web UI (both bypass the
check via a one-shot sentinel - see `display_freshness.request_forced_refresh()`),
or manually create the sentinel yourself:
```bash
sudo touch /var/lib/pi-weather-display/force_refresh_requested
sudo systemctl start pi-weather-display.service
```

## Buttons not switching screen mode

Unlike the render timer, the button listener is a persistent service, so it
should show `Active: active (running)`, not "waiting":
```bash
systemctl status pi-weather-buttons.service
```

View its logs (button presses are logged as they happen):
```bash
journalctl -u pi-weather-buttons.service -f
```

If the service is running but a specific button (B/C/D) doesn't do
anything, note that only button A's GPIO pin has been individually
hardware-confirmed on the reference board - see the `TODO.md` entry on this.
Check the currently-persisted mode directly:
```bash
cat /var/lib/pi-weather-display/screen_mode
```

## Can't reach the web UI, or the device won't reconnect to WiFi

Check the web UI service is up (should show `Active: active (running)`):
```bash
systemctl status pi-weather-web.service
journalctl -u pi-weather-web.service -f
```

If no known network is reachable, the device hosts its own setup AP
(`InkyPiZero-XXXX`) and shows its SSID/password/URL directly on the
e-paper display - see [settings.md](./settings.md#via-the-web-ui-web_apppy-always-on)
and [networking.md](./networking.md) for the full design. Check which mode
it's actually in:
```bash
nmcli -t -f GENERAL.STATE,GENERAL.CONNECTION device show wlan0
systemctl is-active pi-weather-hostapd.service pi-weather-ap-dnsmasq.service
```
`pi-weather-hostapd`/`pi-weather-ap-dnsmasq` active means it's currently
hosting the setup AP; check their own logs
(`journalctl -u pi-weather-hostapd.service -n 50`) if the AP itself doesn't
seem to be broadcasting.

If the device is stuck in AP mode when it shouldn't be (e.g. its known
network really is in range and working), the two most likely causes are a
wrong/changed password for a saved network (fix via the setup AP's own
`/wifi` page, or `nmcli connection show`/`nmcli connection modify` directly
over a serial/keyboard-monitor connection if the device is unreachable any
other way) or the network being temporarily down when the device last
checked (`pi-weather-web.service`'s connectivity check only runs once at
service start, not continuously - restart it once the network's back:
`sudo systemctl restart pi-weather-web.service`).

## Debugging

View the latest logs:
```bash
journalctl -u pi-weather-display.service -n 100
```

Tail the logs (useful while waiting for the next scheduled run):
```bash
journalctl -u pi-weather-display.service -f
```

## Force an immediate render

```bash
sudo systemctl start pi-weather-display.service
```

## Run manually

To diagnose an issue outside of systemd, run the script directly - this
prints logs straight to the terminal:
```bash
sudo /usr/local/pi-weather-display/venv/bin/python /usr/local/pi-weather-display/app/main.py
```

## No EEPROM detected

```bash
RuntimeError: No EEPROM detected! You must manually initialise your Inky board.
```

This project uses the [inky python library](https://github.com/pimoroni/inky)
from Pimoroni to detect and interface with Inky displays. However, the
auto-detect functionality does not work on some boards, which requires
manual setup (see [Manual Setup](https://github.com/pimoroni/inky?tab=readme-ov-file#manual-setup)).

Manually import and instantiate the correct Inky module in
`display/inky_driver.py`. For the 7.3 Inky Impression,
modify the file as follows:
```
@@ -8,8 +8,8 @@
 class InkyDriver:
     def __init__(self, saturation: float = 0.5):
-        from inky.auto import auto
+        from inky.inky_ac073tc1a import Inky
         self.saturation = saturation
-        self.inky_display = auto()
+        self.inky_display = Inky()
         self.inky_display.set_border(self.inky_display.BLACK)
```

Then restart the timer:
```bash
sudo systemctl restart pi-weather-display.timer
```

## Colors look washed out or incorrect

Some color inaccuracies are expected due to the physical limitations of
e-ink displays, especially on multi-color panels with a limited color
palette and dithering.

Image/saturation adjustments can be made via the web UI's
[`/settings` page](./settings.md#via-the-web-ui-web_apppy-always-on) or
directly in `config.py` (see [settings.md](./settings.md) for every option).
The `inky_saturation` field controls the saturation of the palette the image
is dithered to by the `inky` library; try `0` first, which tends to improve
image quality. See
[this response](https://github.com/pimoroni/inky/issues/225#issuecomment-3213935144)
from the Pimoroni team for more details.

## Known Issues during Pi Zero W Installation

Due to limitations with the Pi Zero W, there are some known issues during
installation. For more details and community discussion, refer to this
[GitHub Issue](https://github.com/fatihak/InkyPi/issues/5) on the upstream
project (same underlying hardware/pip issues apply here).

### Pip Installation Error

#### Error message
```bash
WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))':
```

#### Recommended solution
Manually install the required pip packages in the venv:
```bash
source "/usr/local/pi-weather-display/venv/bin/activate"
pip install -r install/requirements.txt
deactivate
```
Restart the timer to apply the changes:
```bash
sudo systemctl restart pi-weather-display.timer
```

### Numpy/Pillow ImportError

#### Error message
```bash
ImportError: Error importing numpy: you should not try to import numpy from
its source directory; please exit the numpy source tree, and relaunch
your python interpreter from there.
```

#### Recommended solution
Manually reinstall Pillow in the venv:
```bash
sudo su
source "/usr/local/pi-weather-display/venv/bin/activate"
pip uninstall Pillow
pip install Pillow
deactivate
```
Restart the timer to apply the changes:
```bash
sudo systemctl restart pi-weather-display.timer
```
