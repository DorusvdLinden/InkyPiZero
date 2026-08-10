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
| Original | `"original"` | Dashed lines at the day's actual min/max (+ a 0°C line if it goes below freezing) | 2x3 grid, 6 cells: wind/humidity/pressure/UV/visibility/**Kwaliteit & Pollen** (combined AQI+pollen) |
| Gridlines | `"gridlines"` (**default**, `DEFAULT_MODE`) | Fixed dotted reference grid every 10°C across the visible range | 2x3 grid, same 6 cells as Original |
| Compact | `"compact"` | Same gridlines style as above | Only wind/humidity/UV/**Kwaliteit & Pollen** (`canvas.COMPACT_KINDS`) - 4 cells (2x2, or 1x4, see `compact_style`) |

If the state file is missing or contains something outside `VALID_MODES`,
`get_mode()` falls back to `DEFAULT_MODE`.

### Kwaliteit & Pollen (combined air quality + pollen)

One data point (`kind: "aqi"` internally, unchanged) shows the **worst of**
European AQI and pollen severity, using the AQI gauge icon in both screen
families. Confirmed with the user 2026-08-10 after finding the separate
pollen indicator (see `docs/changes.md` entry 22) was too easy to read as
"fine" on a day pollennieuws.nl rated unfavorable, when AQI itself was
actually fine and pollen was the real story, or vice versa - a single
combined "how bad is the air for you right now" reading is more useful
than two cards that can disagree.

- **AQI** (`european_aqi`, current-hour reading): `aqi_tier_index =
  min(int(current_aqi // 20), 5)` - Open-Meteo's own 6-tier scale (Goed/
  Redelijk/Matig/Slecht/Zeer slecht/Extreem), same as before.
- **Pollen** (`weather_data._classify_pollen`): all 6 Open-Meteo pollen
  species (alder, birch, grass, mugwort, olive, ragweed - Europe-only,
  null outside each species' active season), classified using each
  species' **peak value anywhere in the current calendar day**
  (`_value_max_today`, not the exact current-hour reading AQI/UV/humidity
  use - pollen swings hard hour to hour, so a single instant can sit at a
  local dip while the rest of the day is a genuine "watch out" day;
  confirmed against pollennieuws.nl). Returns a 0-3 tier index
  (Laag/Matig/Hoog/Zeer hoog) plus the driving species, or `None` if every
  species is null all day.
- **Combining** (`weather_data._combine_aqi_pollen_tier`): both inputs map
  onto one new 4-tier scale, `COMBINED_TIERS = ["Goed", "Matig", "Slecht",
  "Zeer slecht"]` - a fresh scale chosen (not simply reusing AQI's 6 or
  pollen's 4 outright) so both inputs can reach every tier symmetrically.
  AQI's 6 tiers fold onto it via `_AQI_TIER_TO_COMBINED = [0, 0, 1, 2, 3,
  3]`; pollen's 4 tiers already match 1:1. The displayed measurement is
  `COMBINED_TIERS[max(aqi_combined, pollen_tier_index)]`; when only one
  input has data, that one drives it alone; when neither does, shows
  "N/A". The driving pollen species is shown as a second word (e.g. "Zeer
  slecht Berk") only when pollen's tier is at or above AQI's contribution
  - when AQI is the sole or bigger driver, no species is named.
- **Gauge needle** (`weather_data.get_combined_rotation`): reuses
  `render_aqi_gauge`'s existing 4 color bands unchanged (very_high/high/
  moderate/low), needle centered in the band matching the combined tier
  index - driven by the tier index rather than a literal 0-100 AQI value,
  so the needle position stays honest even when pollen (not AQI) is
  driving a bad reading.

No standalone pollen icon or cell exists anymore - visibility is shown
unconditionally again (no more swap), and compact mode is always exactly 4
cells (no more variable 4-or-5). See `scripts/test_pollen_scenarios.py`
for deterministic coverage of every combined tier, which input wins ties,
and the no-data fallback.

Note Open-Meteo/CAMS only models the 6 pollen species above - Dutch pollen
services like pollennieuws.nl group mugwort+ragweed (and sometimes other
weeds not modeled here, e.g. nettle/sorrel/plantain) under a broader
"Kruiden" category, so this app's pollen contribution can understate what a
Netherlands-focused service reports even when both are working correctly -
a real, permanent data-source gap (see `TODO.md`), not a bug.

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
