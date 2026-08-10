# Settings & Options

Reference for every user-facing option in InkyPiZero: what it does, where it
lives, and how to change it. There are three ways to change settings, in
increasing order of how much they cover: the four physical buttons (screen
mode only), the always-on web UI (every `config.py` field, plus WiFi/
shutdown), and editing `config.py` directly in source (everything, but
requires a `git pull` on the device to take effect).

Keep this file up to date whenever a setting is added, renamed, removed, or
its default changes - see the standing rule in [CLAUDE.md](../CLAUDE.md).

## Via the physical buttons (`button_listener.py`)

The only settings changeable without editing code. `button_listener.py` runs
as its own persistent service (`pi-weather-buttons.service`) and listens on
GPIO for falling-edge presses, debounced 50ms (`DEBOUNCE_MS`).

| Button | GPIO (BCM) | Action |
|---|---|---|
| A | 5 (hardware-confirmed) | Blank the display and shut the Pi down (`blank_and_shutdown()`) |
| B | 6 | Switch to `"original"` screen mode |
| C | 16 | Switch to `"gridlines"` screen mode |
| D | 24 | Switch to `"compact"` screen mode |

B/C/D=GPIO6/16/24 follow Pimoroni's standard 4-button layout but, unlike A,
haven't been individually hardware-verified on this specific board.

Pressing B/C/D calls `display_mode.set_mode(mode)` then forces an immediate
re-render (`systemctl start pi-weather-display.service`) so the new layout
shows right away instead of waiting for the next timer tick.

### Screen modes (`display_mode.py`)

The active mode persists to `/var/lib/pi-weather-display/screen_mode` (a
plain text file - `main.py` is a one-shot timer job with no memory between
runs, so this is how the choice survives across renders).

| Mode | `VALID_MODES` value | Chart style | Data-point grid |
|---|---|---|---|
| Original | `"original"` | Dashed lines at the day's actual min/max (+ a 0°C line if it goes below freezing) | 2x3 grid, always 6 cells: wind/humidity/pressure/UV/AQI, plus a 5th "swap" cell - pollen when available, else visibility |
| Gridlines | `"gridlines"` (**default**, `DEFAULT_MODE`) | Fixed dotted reference grid every 10°C across the visible range | 2x3 grid, same 6 cells as Original |
| Compact | `"compact"` | Same gridlines style as above | Only wind/humidity/UV/AQI (`canvas.COMPACT_KINDS`) normally - 4 cells (2x2, or 1x4, see `compact_style`); grows to 5 cells (3-over-2, or 1x5) whenever pollen data is available |

If the state file is missing or contains something outside `VALID_MODES`,
`get_mode()` falls back to `DEFAULT_MODE`.

### Pollen (Hooikoorts)

Open-Meteo's air-quality endpoint (the same one already used for UV/AQI)
also serves hourly pollen concentrations, but only for **European
locations** and only during each species' **active season** - null
otherwise. `weather_data._classify_pollen` checks all 6 species (alder,
birch, grass, mugwort, olive, ragweed) for the current hour and returns
the worst tier (Laag/Matig/Hoog/Zeer hoog) plus the species driving it, or
`None` if every species is null. When `None`, the app falls back to
showing visibility instead - this is why pollen isn't a guaranteed 7th
data point: most non-European renders, and any European one outside the
season, simply won't have it. See `scripts/test_pollen_scenarios.py` for
deterministic coverage of every tier plus the fallback.

## Via the web UI (`web_app.py`, always-on)

A small always-on Flask service (`pi-weather-web.service`), reachable at
`http://<device IP>:8080`, running completely independently of the render
timer - see [networking.md](./networking.md) for the network-mode
architecture underneath it. No authentication anywhere (matches button A's
existing unauthenticated-shutdown precedent) - trusted-LAN-only by design.

| Page | What it does |
|---|---|
| `/` | Status overview (current WiFi mode, current screen mode) + links |
| `/settings` | Every `config.py`/`DisplayConfig` field below, as a form |
| `/wifi` | Add/edit/remove saved WiFi networks (never auto-removes existing ones) |
| `/shutdown` | Same action as physical button A, with a confirmation step |

Settings saved here are written to
`/var/lib/pi-weather-display/settings.json` (`settings_store.py`) rather
than editing `config.py` itself - `main.py` loads this file as an overlay
on top of `config.py`'s dataclass defaults (`settings_store.load_config()`),
so a missing file or an individual invalid field just falls back to the
matching default instead of ever breaking a render. Saving triggers an
immediate re-render, the same `systemctl start pi-weather-display.service`
precedent the physical buttons already use.

If no known WiFi network is reachable, the device instead hosts its own
setup AP and shows the SSID/password/URL directly on the e-paper display -
see [networking.md](./networking.md) for the full AP-hosting design
(hostapd-based, not NetworkManager's native hotspot - that was tried first
and reproducibly failed on this hardware).

## Via code (`config.py` - `DisplayConfig`)

`config.py`'s `DisplayConfig` dataclass defaults are the fallback for
anything not overridden by a saved `settings.json` (see above) - edited
directly in source for a change that should apply device-wide with no web
UI involved (installer prints a reminder to do this on first setup). All
fields:

| Field | Default | Effect |
|---|---|---|
| `latitude`, `longitude` | Sittard, NL (51.0004365, 5.8993687) | Location passed to every Open-Meteo/Nominatim request |
| `units` | `"metric"` | `"metric"` \| `"imperial"` \| `"standard"` - controls temperature/speed/distance units *and* (since the precip-label feature) whether rain/hail is "mm" or "in" and snow is "cm" or "in" (`UNITS` dict, `weather_data.py`) |
| `timezone` | `"Europe/Amsterdam"` | IANA tz name; only used as a fallback if Open-Meteo's response omits its own `timezone` field |
| `time_format` | `"24h"` | `"24h"` \| `"12h"` - hour labels on the chart and the header's "Laatste update" time |
| `forecast_days` | `7` | Number of forecast cards shown in the bottom row (today is excluded from the row itself; `fetch_snapshot` internally requests `forecast_days + 1` days from Open-Meteo) |
| `graph_icon_step` | `2` | Draw an hourly weather icon (and x-axis tick/label) every Nth hour on the chart, instead of every hour |
| `show_moon_phase` | `False` | Whether forecast cards show the moon-phase icon + illumination % (bottom-left of each card) |
| `background_color` | `"#ffffff"` | Canvas background (hex) |
| `text_color` | `"#000000"` | Default text/line color (hex) |
| `inky_saturation` | `0.0` | 0.0-1.0 blend between the panel's desaturated and fully-saturated native palettes (see [Color palette](#color-palette-widgetspalettepy) below) - **must** match `widgets/palette.py`'s hardcoded `PALETTE = Palette(saturation=0.0)` singleton, they aren't wired together |
| `refresh_interval_seconds` | `600` | **Currently unused/vestigial** - not read anywhere in the codebase. The actual render cadence is `install/pi-weather-display.timer`'s `OnUnitActiveSec=10min`, a separately hardcoded value. Changing this field alone does nothing; see [Install-time settings](#install-time-settings) to actually change the cadence |

## Via CLI flags (`main.py`, local/dev use only)

Not available on the deployed Pi (the systemd service invokes `main.py` with
no arguments) - only relevant when running `python main.py` by hand.

| Flag | Values | Effect |
|---|---|---|
| `--mock-output <path>` | any file path | Render to a PNG via `display/mock_driver.py` instead of driving real Inky hardware |
| `--screen-mode` | `original` \| `gridlines` \| `compact` | Override the button-selected mode (`display_mode.get_mode()`) for one render |
| `--compact-style` | `icon_left` (default) \| `icon_above` \| `icon_above_row` | Which of the three "compact" mode mockup layouts to use - see `canvas.WeatherCanvas._draw_data_points_compact` |

`--compact-style` has no button/persisted-state equivalent - `icon_left` is
the only style wired up for real use; the other two remain as comparison
mockups.

## Install-time settings

Not runtime settings, but the only other place cadence/identity get
configured:

- **Render cadence**: `install/pi-weather-display.timer`'s `OnUnitActiveSec`
  (default `10min`) plus `OnBootSec=30s` for the first run after boot. Edit
  the file and rerun `sudo bash install/install.sh` (safe to rerun) to apply.
- **Install location**: `install/install.sh`'s `APPNAME="pi-weather-display"`
  controls both the systemd unit names and the install path
  (`/usr/local/$APPNAME`); `BUTTONS_APPNAME="pi-weather-buttons"` likewise
  for the button-listener service.
- **Display saturation at the hardware layer**: `display/inky_driver.py`'s
  `InkyDriver(saturation=config.inky_saturation)` - reads `config.py`
  directly, see above.

## Color palette (`widgets/palette.py`)

Not a "setting" in the adjustable-knob sense, but the one place a would-be
setting silently *isn't* wired to `config.py`: `PALETTE = Palette(saturation=0.0)`
is a module-level singleton computed once at import time. If
`DisplayConfig.inky_saturation` is ever changed from `0.0`, this line must be
changed to match by hand, or authored colors (icons, chart lines, gauges)
will stop being exact palette matches and start dithering. See
`scripts/panel_sim.py` (preview at the actual driven saturation) and
`scripts/color_options.py` (side-by-side comparison at other saturations).
