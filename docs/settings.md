# Settings & Options

Reference for every user-facing option in InkyPiZero: what it does, where it
lives, and how to change it. There are three ways to change settings, in
increasing order of how much they cover: the four physical buttons (screen
mode only), the always-on web UI (every `config.py` field, plus WiFi/
shutdown), and editing `config.py` directly in source (everything, but
requires a `git pull` on the device to take effect).

Keep this file up to date whenever a setting is added, renamed, removed, or
its default changes - see the standing rule in [CLAUDE.md](../CLAUDE.md).

## Display refresh cadence (`display_freshness.py`)

`install/pi-weather-display.timer` still fires every 10 minutes (fetching
fresh weather data every time), but `main.py` only actually **pushes to the
physical panel** when it's worth the wear/flash of a real e-paper refresh:

- The main current-conditions icon or the big temperature number changed
  since the last refresh, **or**
- More than an hour has passed since the last refresh (keeps slower-moving
  details - forecast cards, the hourly chart, "Laatste update", sunrise/
  sunset, moon phase - from going stale indefinitely during a long stretch
  of unchanged weather), **or**
- A screen-mode button press or a web-UI settings save requested an
  immediate refresh (see below) - these always show up right away,
  regardless of whether the icon/temperature changed.

Otherwise the tick is skipped entirely - no canvas render, no display
write, just a log line. State persists to
`/var/lib/pi-weather-display/display_freshness.json` (same one-shot-job
persistence pattern as `display_mode.py`): last-shown icon key,
temperature, and refresh timestamp. A missing or corrupt state file is
treated as "never refreshed" (always refreshes) rather than crashing the
render pipeline.

Button presses (`button_listener.py`'s `switch_mode()`) and settings saves
(`web/routes.py`'s `_trigger_rerender()`) both write a one-shot sentinel
file (`display_freshness.request_forced_refresh()`) immediately before
forcing the render service to start, so `main.py` knows to bypass the
skip check for that one run - a user-triggered change is never silently
dropped because the icon/temperature happened to be unchanged.

This is **not** configurable via `config.py`/the web UI - the 10-minute
fetch cadence and the 1-hour force-refresh ceiling are both hardcoded
(`display_freshness.MAX_STALE`). `--mock-output` (local testing/preview)
always renders, bypassing this check entirely - see
`scripts/test_display_freshness.py` for deterministic coverage of every
branch.

## Via the physical buttons (`button_listener.py`)

The only settings changeable without editing code. `button_listener.py` runs
as its own persistent service (`pi-weather-buttons.service`) and listens on
GPIO for falling-edge presses, debounced 50ms (`DEBOUNCE_MS`).

| Button | GPIO (BCM) | Action |
|---|---|---|
| A | 5 (hardware-confirmed) | Blank the display and shut the Pi down (`blank_and_shutdown()`) |
| B | 6 (hardware-confirmed) | Switch to `"original"` screen mode |
| C | 16 (hardware-confirmed) | Switch to `"gridlines"` screen mode |
| D | 24 (hardware-confirmed) | Switch to `"compact"` screen mode |

All four buttons follow Pimoroni's standard 4-button GPIO layout and have
each been individually confirmed on the real board (press -> correct
screen mode switches).

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
than two cards that can disagree. This section documents exactly how each
input's raw number becomes a tier, and how the two tiers combine into one.

#### Input 1: AQI's scale

Open-Meteo's `european_aqi` is already a composite 0-100+ index (it
folds several pollutants into one number upstream - InkyPiZero doesn't
compute AQI itself, only buckets the value Open-Meteo returns). Read at
the **current hour** (`_value_at_current_hour`, same live-instant pattern
UV/humidity use - unlike pollen, see below). Bucketed into 20-point bands:

```python
aqi_tier_index = min(int(current_aqi // 20), 5)
```

| `current_aqi` range | `aqi_tier_index` | AQI's own tier name (NL) |
|---|---|---|
| 0-19 | 0 | Goed |
| 20-39 | 1 | Redelijk |
| 40-59 | 2 | Matig |
| 60-79 | 3 | Slecht |
| 80-99 | 4 | Zeer slecht |
| 100+ | 5 | Extreem |

`min(..., 5)` clamps anything ≥100 into the last bucket rather than
indexing out of range - AQI values above 100 are possible but rare.
`current_aqi is None` (data unavailable) leaves `aqi_tier_index = None`,
handled explicitly further down rather than defaulting to a fake tier.

#### Input 2: pollen's scale

`weather_data._classify_pollen` checks all 6 Open-Meteo pollen species
(alder, birch, grass, mugwort, olive, ragweed - Europe-only, null outside
each species' active season) and returns a single worst-species result.
Two things about *how* it gets there are worth understanding in detail:

**1. Two separate threshold tables, not one.** Tree pollen and grass/weed
pollen are shed in very different absolute concentrations, so a single
grains/m³ scale can't sensibly cover both - these are the commonly cited
European pollen-count bands (`weather_data.py:277-278`), picked since no
single authoritative scale exists (noted inline in the code):

| Tier | Tree species (Els/Berk/Olijf) grains/m³ | Grass & weed (Gras/Bijvoet/Ambrosia) grains/m³ |
|---|---|---|
| Laag (0) | ≤10 | ≤5 |
| Matig (1) | ≤100 | ≤20 |
| Hoog (2) | ≤1000 | ≤50 |
| Zeer hoog (3) | >1000 | >50 |

`_pollen_tier_index(species, value)` walks a species' threshold tuple in
order and returns the first tier whose cutoff the value doesn't exceed
(falling through to index 3 - Zeer hoog - if it exceeds every cutoff).

**2. Each species' *peak value anywhere in the current calendar day***,
not the current hour (`_value_max_today`) - a deliberate exception to the
current-hour pattern AQI/UV/humidity use. Pollen swings hard hour to hour
(Sittard's grass count ranged 4.4-9.8 grains/m³ across one real day), so a
single instant can sit at a local dip while the rest of the day is a
genuine "watch out" day - confirmed against pollennieuws.nl's own daily
framing.

**Picking the worst species**: every species with data today gets a
`(tier_index, normalized_value)` pair, where `normalized_value = value /
thresholds[-1]` (the value as a fraction of its *own* group's top
threshold - 1000 for tree, 50 for grass/weed). The species with the
highest `(tier_index, normalized_value)` tuple wins - tier first, then
normalized concentration to break same-tier ties. Normalizing this way is
what lets a tree species and a grass/weed species be compared fairly for
tie-breaking despite their raw thresholds differing 20x. This tie-break
exists because Open-Meteo reports an out-of-season species as a flat
`0.0` rather than dropping it from the response - without normalized
comparison, alphabetically/insertion-first species like alder would win
"worst" over a genuinely active one just by always being *present* (if
compared by tier alone, a tie at "Laag" would fall to whichever species
happened to be checked first).

The winning species' tier index (0-3) feeds the combined scale below
directly - `POLLEN_TIERS` is a deliberate 1:1 index match for
`COMBINED_TIERS`. Its species also collapses to one of 3 broad categories
for the on-screen cause label (`_pollen_category_nl`, confirmed with the
user 2026-08-10): **Boom** (alder/birch/olive), **Gras** (grass), or
**Ambrosia** (mugwort/ragweed - named for the more severe of the two weed
species, not a literal per-species mapping).

If every species is null all day (out of season, or a non-European
location), `_classify_pollen` returns `None`.

#### Combining the two into one 4-tier scale

Rather than reuse either input's native scale outright (AQI's 6, pollen's
4), both map onto a **fresh 4-tier scale** chosen so both inputs can reach
every tier symmetrically - confirmed with the user 2026-08-10:

```python
COMBINED_TIERS = ["Goed", "Matig", "Slecht", "Zeer slecht"]
```

AQI's 6 tiers fold onto it via a fixed lookup table:

| `aqi_tier_index` | AQI tier name | `_AQI_TIER_TO_COMBINED` | Combined tier |
|---|---|---|---|
| 0 | Goed | 0 | Goed |
| 1 | Redelijk | 0 | Goed |
| 2 | Matig | 1 | Matig |
| 3 | Slecht | 2 | Slecht |
| 4 | Zeer slecht | 3 | Zeer slecht |
| 5 | Extreem | 3 | Zeer slecht |

Pollen's 4 tiers need no lookup table - they already match 1:1:

| `tier_index` (from `_classify_pollen`) | Pollen tier name | Combined tier |
|---|---|---|
| 0 | Laag | Goed |
| 1 | Matig | Matig |
| 2 | Hoog | Slecht |
| 3 | Zeer hoog | Zeer slecht |

The final tier is simply the worse of the two mapped values -
`_combine_aqi_pollen_tier`:

```python
combined_index = max(aqi_combined, pollen_tier_index)  # whichever inputs are present
```

- Both present -> worse of the two wins.
- Only one present -> that one alone decides (the other contributes
  nothing, doesn't drag the result toward "Goed").
- Neither present -> `None`, displayed as `"N/A"`.

The driving pollen **category** (Boom/Gras/Ambrosia) is appended after a
colon (e.g. "Zeer slecht: Boom") only when **both** of these hold
(confirmed with the user 2026-08-10):
- `pollen_tier_index > 0` - pollen is at least Matig, not Laag. Even if
  pollen ties or beats AQI's contribution, "Laag" isn't worth naming a
  cause for - the measurement alone ("Goed") already says everything's
  fine.
- `pollen_tier_index >= aqi_combined` - pollen's contribution is at or
  above AQI's.

When either doesn't hold - AQI is the bigger driver, or pollen is
Laag/absent - no category is named, and the measurement displays alone
with no trailing colon (`WeatherCanvas._data_point_value_text`'s
`unit_separator` field controls the `": "` - a per-data-point override,
every other data point still uses a plain space before its unit).

#### Gauge needle: reusing the same 4 color bands

`render_aqi_gauge` draws 4 fixed 45°-wide colored arc bands
(`widgets/gauge.py:151-156`) - unchanged from before pollen existed, this
is the exact same dial the standalone AQI cell always used:

| Arc angle range | Band | Color | Combined tier it now represents |
|---|---|---|---|
| 180°-225° | `aqi_band_very_high` | red | Zeer slecht (3) |
| 225°-270° | `aqi_band_high` | orange | Slecht (2) |
| 270°-315° | `aqi_band_moderate` | yellow | Matig (1) |
| 315°-360° | `aqi_band_low` | green | Goed (0) |

Previously the needle's rotation came from a literal 0-100 AQI value
(linear across the full arc). Now `get_combined_rotation(combined_index)`
instead centers the needle in the band matching the **tier index**:

```python
tier_from_worst = 3 - combined_tier_index
rotation_deg = get_aqi_rotation_from_fraction((tier_from_worst + 0.5) / 4)
```

| `combined_index` | Combined tier | Needle rotation | Lands in band |
|---|---|---|---|
| 0 | Goed | -22.5° | low/green (center) |
| 1 | Matig | -67.5° | moderate/yellow (center) |
| 2 | Slecht | -112.5° | high/orange (center) |
| 3 | Zeer slecht | -157.5° | very_high/red (center) |

This is deliberate: if the needle still came from a literal AQI number,
it would point to a "fine" position even when the *displayed text* says
"Zeer slecht" because pollen (not AQI) is driving the reading - a
misleading mismatch. Driving the needle from the tier index instead keeps
icon and text always consistent, whichever input is worse.
`combined_index is None` (neither input has data) falls back to a neutral
middle rotation (`fraction_good = 0.5`, needle pointing straight down,
between the moderate and high bands) rather than defaulting toward either
extreme.

#### Worked examples

| AQI | Pollen | Displayed | Why |
|---|---|---|---|
| 15 (Goed) | no data | "Goed" | AQI alone decides |
| 50 (Matig) | no data | "Matig" | AQI alone decides |
| 90 (Zeer slecht, combined 3) | grass 3 grains/m³ (Laag, combined 0) | "Zeer slecht" | AQI is the bigger driver (3 > 0) |
| 10 (Goed, combined 0) | birch 2000 grains/m³ (Zeer hoog, combined 3) | "Zeer slecht: Boom" | pollen is the bigger driver (3 > 0) |
| 45 (Matig, combined 1) | grass 15 grains/m³ (Matig, combined 1) | "Matig: Gras" | tied at combined 1, and pollen is genuinely elevated (tier > 0) |
| 30 (Redelijk, combined 0) | grass 3 grains/m³ (Laag, combined 0) | "Goed" | tied at combined 0, but pollen is only Laag - no category named |
| no data | no data | "N/A" | neither input available |

See `scripts/test_pollen_scenarios.py` for these and more as executable,
deterministic assertions (every combined tier, tie-breaking, the
daily-peak-vs-current-hour behavior, and the no-data fallback) - live
weather can't reliably guarantee a specific AQI+pollen combination on any
given run.

No standalone pollen icon or cell exists anymore - visibility is shown
unconditionally again (no more swap), and compact mode is always exactly 4
cells (no more variable 4-or-5).

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
