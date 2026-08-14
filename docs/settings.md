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

`install/pi-weather-display.timer` still fires every 10 minutes (a fixed,
root-owned systemd cadence, not configurable via `config.py`/the web UI -
rewriting it from the web app would need root and risks breaking the
render pipeline or `install.sh`'s "safe to rerun any time" idempotency).
On top of that fixed tick, two independent, web-UI-configurable throttles
decide how much actually happens:

1. **`min_update_interval_minutes`** (default `0`) - checked first, before
   even fetching weather data. `0` means no extra throttling beyond the
   timer's own 10-minute cadence; a higher value skips a tick entirely -
   no fetch, no render - until that many minutes have passed since the
   last check. Use this to fetch/check less often than every 10 minutes
   without touching the systemd timer itself.
2. **`force_refresh_max_stale_minutes`** (default `60`) - once data has
   been fetched, `main.py` only actually **pushes to the physical panel**
   when it's worth the wear/flash of a real e-paper refresh:
   - The main current-conditions icon or the big temperature number
     changed since the last refresh, **or**
   - More than `force_refresh_max_stale_minutes` has passed since the
     last refresh (keeps slower-moving details - forecast cards, the
     hourly chart, "Laatste update", sunrise/sunset, moon phase - from
     going stale indefinitely during a long stretch of unchanged
     weather), **or**
   - A screen-mode button press or a web-UI settings save requested an
     immediate refresh (see below) - these always show up right away,
     regardless of whether the icon/temperature changed, and also bypass
     `min_update_interval_minutes`.

   Otherwise the tick is skipped entirely - no canvas render, no display
   write, just a log line.

State persists to `/var/lib/pi-weather-display/display_freshness.json`
(same one-shot-job persistence pattern as `display_mode.py`): last-check
timestamp, last-shown icon key, temperature, and last-display timestamp
all share the one file (read-modify-write, so recording one doesn't
clobber the other). A missing or corrupt state file is treated as "never
checked/refreshed" (always proceeds) rather than crashing the render
pipeline.

Button presses (`button_listener.py`'s `switch_mode()`) and settings saves
(`web/routes.py`'s `_trigger_rerender()`) both write a one-shot sentinel
file (`display_freshness.request_forced_refresh()`) immediately before
forcing the render service to start, so `main.py` knows to bypass both
throttles for that one run - a user-triggered change is never silently
dropped because the icon/temperature happened to be unchanged or the
minimum interval hadn't elapsed.

`--mock-output` (local testing/preview) always renders, bypassing both
throttles entirely - see `scripts/test_display_freshness.py` for
deterministic coverage of every branch.

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
| Compact | `"compact"` | Same gridlines style as above | Only wind/humidity/UV/**Kwaliteit & Pollen** (`canvas.COMPACT_KINDS`) - 2x2 grid, 4 bigger cells |

If the state file is missing or contains something outside `VALID_MODES`,
`get_mode()` falls back to `DEFAULT_MODE`.

### Kwaliteit & Pollen (combined air quality + pollen)

One data point (`kind: "aqi"` internally, unchanged) shows the **worst of**
RIVM's official Dutch air-quality index and pollen severity, using the AQI
gauge icon in both screen families. Originally built on Open-Meteo's
`european_aqi` (confirmed with the user 2026-08-10) after finding the
separate pollen indicator (see `docs/changes.md` entry 22) was too easy to
read as "fine" on a day pollennieuws.nl rated unfavorable, when AQI itself
was actually fine and pollen was the real story, or vice versa - a single
combined "how bad is the air for you right now" reading is more useful
than two cards that can disagree. The AQI *source* changed 2026-08-14:
comparing a live reading against
[longfonds.nl/gezondelucht](https://www.longfonds.nl/gezondelucht) (which
uses RIVM's own ground-station data) showed Open-Meteo's modeled
`european_aqi` disagreeing with RIVM's own measurement for the configured
location - Open-Meteo's AQI is a coarse-resolution model (Copernicus CAMS),
not a real Dutch sensor reading. Swapped to RIVM's own measurement network
(luchtmeetnet.nl's open API) instead. Pollen stays on Open-Meteo - RIVM
doesn't publish pollen data. This section documents exactly how each
input's raw number becomes a tier, and how the two tiers combine into one.

#### Input 1: RIVM's LKI scale

`weather_data._get_rivm_current_lki` reads the current **LKI**
(Luchtkwaliteitsindex, RIVM's own national air-quality index) from
[luchtmeetnet.nl](https://www.luchtmeetnet.nl/) - a keyless, fair-use
public API (the API itself reports a 300 requests/5 minutes limit, seen
directly in its own 429 response during testing). LKI is a real
ground-station measurement, 1-11, with 5 official named bands:

```python
def _lki_tier_index(lki: int) -> int:
    if lki <= 3: return 0
    elif lki <= 6: return 1
    elif lki <= 8: return 2
    elif lki <= 10: return 3
    return 4
```

| LKI range | `_lki_tier_index` | Category (NL) |
|---|---|---|
| 1-3 | 0 | Goed |
| 4-6 | 1 | Matig |
| 7-8 | 2 | Onvoldoende |
| 9-10 | 3 | Slecht |
| 11 | 4 | Zeer slecht |

**Finding the right station.** luchtmeetnet has no geo-filter query
param, so `_resolve_rivm_station` lists every station (paginated) and
fetches each one's geometry to compute distance to the configured
coordinates - not every station publishes LKI (some are traffic-only
sensors), so the nearest candidate that actually has LKI data wins, capped
at `RIVM_MAX_STATION_DISTANCE_KM` (150km, generously covering all of NL)
so a non-Dutch location correctly falls back to no data instead of
"succeeding" with whatever Dutch station happens to be globally nearest.
For the repo's default coordinates this resolves to `NL50003`
(Geleen-Asterstraat, ~5.7km away).

That's roughly 130 requests, run only once per location and then cached to
`/var/lib/pi-weather-display/rivm_station_cache.json`
(`{"latitude", "longitude", "station_number"}`) - every other call is a
single cheap LKI request. The cache is re-resolved whenever the configured
`latitude`/`longitude` no longer match it, which happens promptly (not
just eventually) when the location is changed via the settings web UI:
saving new coordinates already calls `_trigger_rerender()`
(`web/routes.py`), forcing an immediate re-render rather than waiting for
the next scheduled timer tick - and that forced render is exactly when the
cache mismatch gets detected and the station re-resolved.

**Fails soft throughout**, same as `_reverse_geocode`'s existing pattern: a
resolution failure, a rate-limited/unreachable API, or no station within
range just leaves the LKI arm absent for that render tick (pollen alone
decides the combined tier, or "N/A" if pollen's also unavailable) rather
than aborting the whole render.

Read once per render, not per hour - LKI has no forecast, only a current
reading (unlike Open-Meteo's hourly-array pattern UV/humidity/pollen use).

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

The winning species' tier index (0-3) feeds the combined scale below via
`POLLEN_TIER_TO_COMBINED` (pollen's 4 tiers no longer match `COMBINED_TIERS`
1:1 now that it's 5 tiers - see below). Its species also collapses to one
of 3 broad categories for the on-screen cause label (`_pollen_category_nl`,
confirmed with the user 2026-08-10): **Boom** (alder/birch/olive), **Gras**
(grass), or **Ambrosia** (mugwort/ragweed - named for the more severe of
the two weed species, not a literal per-species mapping).

If every species is null all day (out of season, or a non-European
location), `_classify_pollen` returns `None`.

#### Combining the two into one 5-tier scale

Since LKI is itself a direct, 5-tier "how bad is the air" index (see
above), `COMBINED_TIERS` adopts LKI's own scale and names verbatim rather
than inventing a fresh one - LKI maps onto it **1:1**, no fold table, no
rounding judgment call needed on that side:

```python
COMBINED_TIERS = ["Goed", "Matig", "Onvoldoende", "Slecht", "Zeer slecht"]
```

Pollen's narrower 4 tiers don't align 1:1 with 5, so *they* need the fold
now (the reverse of the old Open-Meteo-AQI design, where AQI needed the
fold and pollen matched 1:1):

```python
POLLEN_TIER_TO_COMBINED = [0, 1, 3, 4]  # Laag, Matig, Hoog, Zeer hoog
```

| `tier_index` (from `_classify_pollen`) | Pollen tier name | `POLLEN_TIER_TO_COMBINED` | Combined tier |
|---|---|---|---|
| 0 | Laag | 0 | Goed |
| 1 | Matig | 1 | Matig |
| 2 | Hoog | 3 | **Slecht** |
| 3 | Zeer hoog | 4 | Zeer slecht |

"Hoog" pollen rounds *up* to "Slecht", skipping "Onvoldoende" entirely,
rather than rounding down into it - a deliberate round-toward-worse choice
(the whole motivation for this change was that the old AQI mapping
under-stated severity, e.g. Open-Meteo's "Redelijk" collapsing into
"Goed"; the new mapping shouldn't reintroduce that in a different form).
One consequence: pollen alone can never produce "Onvoldoende" - only LKI
can. That's fine, since `max()`-combining below doesn't require both
inputs to cover the same range, only that neither's contribution gets
understated.

The final tier is simply the worse of the two mapped values -
`_combine_aqi_pollen_tier`:

```python
combined_index = max(lki_tier_index, pollen_combined_index)  # whichever inputs are present
```

- Both present -> worse of the two wins.
- Only one present -> that one alone decides (the other contributes
  nothing, doesn't drag the result toward "Goed").
- Neither present -> `None`, displayed as `"N/A"`.

The driving pollen **category** (Boom/Gras/Ambrosia) is appended after a
colon (e.g. "Zeer slecht: Boom") only when **both** of these hold
(confirmed with the user 2026-08-10):
- `pollen_tier_index > 0` - pollen is at least Matig, not Laag. Even if
  pollen ties or beats LKI's contribution, "Laag" isn't worth naming a
  cause for - the measurement alone ("Goed") already says everything's
  fine.
- `pollen_combined_index >= lki_combined` - pollen's (mapped) contribution
  is at or above LKI's.

When either doesn't hold - LKI is the bigger driver, or pollen is
Laag/absent - no category is named, and the measurement displays alone
with no trailing colon (`WeatherCanvas._data_point_value_text`'s
`unit_separator` field controls the `": "` - a per-data-point override,
every other data point still uses a plain space before its unit).

#### Gauge needle: 5 color bands

`render_aqi_gauge` draws 5 fixed 36°-wide colored arc bands
(`widgets/gauge.py`), worst-to-best as the angle increases:

| Arc angle range | Band | Color | Combined tier it represents |
|---|---|---|---|
| 180°-216° | `aqi_band_extreme` | black | Zeer slecht (4) |
| 216°-252° | `aqi_band_very_high` | red | Slecht (3) |
| 252°-288° | `aqi_band_high` | orange | Onvoldoende (2) |
| 288°-324° | `aqi_band_moderate` | yellow | Matig (1) |
| 324°-360° | `aqi_band_low` | green | Goed (0) |

Only 4 rungs (green/yellow/orange/red) fit before running into the
display's fixed 7-color limit, so the 5th/worst band reuses black - same
precedent the UV icon already established for its own "Extreem" tier
(`widgets/palette.py`). A black band means the needle needs a light
outline to stay visible when pointing into it - `aqi_needle_outline`
(white), the same needle+outline technique the pressure gauge already
uses.

`get_combined_rotation(combined_index)` centers the needle in the band
matching the **tier index**, generalized to whatever `COMBINED_TIERS`'s
length is rather than a hardcoded band count:

```python
tier_count = len(COMBINED_TIERS)
tier_from_worst = (tier_count - 1) - combined_tier_index
rotation_deg = get_aqi_rotation_from_fraction((tier_from_worst + 0.5) / tier_count)
```

| `combined_index` | Combined tier | Needle rotation | Lands in band |
|---|---|---|---|
| 0 | Goed | -18° | low/green (center) |
| 1 | Matig | -54° | moderate/yellow (center) |
| 2 | Onvoldoende | -90° | high/orange (center) |
| 3 | Slecht | -126° | very_high/red (center) |
| 4 | Zeer slecht | -162° | extreme/black (center) |

This is deliberate: if the needle still came from a literal LKI number, it
would point to a "fine" position even when the *displayed text* says
"Zeer slecht" because pollen (not LKI) is driving the reading - a
misleading mismatch. Driving the needle from the tier index instead keeps
icon and text always consistent, whichever input is worse.
`combined_index is None` (neither input has data) falls back to a neutral
middle rotation (`fraction_good = 0.5`, needle pointing straight down,
between the moderate/orange bands) rather than defaulting toward either
extreme.

#### Worked examples

| LKI | Pollen | Displayed | Why |
|---|---|---|---|
| 2 (Goed) | no data | "Goed" | LKI alone decides |
| 5 (Matig) | no data | "Matig" | LKI alone decides |
| 7 (Onvoldoende, combined 2) | 10.4 grains/m³ grass (Matig, combined 1) | "Onvoldoende" | LKI is the bigger driver (2 > 1) - a real 2026-08-14 Sittard reading |
| 11 (Zeer slecht, combined 4) | grass 3 grains/m³ (Laag, combined 0) | "Zeer slecht" | LKI is the bigger driver (4 > 0) |
| 2 (Goed, combined 0) | birch 2000 grains/m³ (Zeer hoog, combined 4) | "Zeer slecht: Boom" | pollen is the bigger driver (4 > 0) |
| 5 (Matig, combined 1) | grass 15 grains/m³ (Matig, combined 1) | "Matig: Gras" | tied at combined 1, and pollen is genuinely elevated (tier > 0) |
| 2 (Goed, combined 0) | grass 3 grains/m³ (Laag, combined 0) | "Goed" | tied at combined 0, but pollen is only Laag - no category named |
| no data | no data | "N/A" | neither input available |

See `scripts/test_pollen_scenarios.py` for these and more as executable,
deterministic assertions (every combined tier, tie-breaking, the
daily-peak-vs-current-hour behavior, and the no-data fallback) - live
weather can't reliably guarantee a specific LKI+pollen combination on any
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

### Forecast cards: rain amount + weather-quality border

Each card in the multi-day forecast row (`widgets/forecast.py`) shows two
things beyond the icon and high/low temperature, added 2026-08-14:

- **Rain amount** ("3mm", "0.6mm", etc.) drawn next to the icon, only on
  days where rain is actually expected.
- **A colored border** coding how pleasant that day's weather is overall -
  temperature and precipitation combined, worst-of-both-wins, the same
  `max()` combining idiom the "Kwaliteit & Pollen" gauge above uses.

#### Input 1: temperature tier

Based on the day's `high` (°C), symmetric hot/cold bands - `15-25°C` is
the pleasant middle, both extremes degrade the tier
(`weather_data._temp_quality_tier`):

| Range | Tier |
|---|---|
| < -5°C (strenge vorst) | Zeer slecht |
| -5 to 0°C (vorst) | Slecht |
| 0 to 14°C (koud/koel) | Matig |
| 15 to 25°C (aangenaam) | **Goed** |
| 26 to 31°C (warm) | Slecht |
| ≥ 32°C (hittegolf) | Zeer slecht |

#### Input 2: precipitation tier

Based on Open-Meteo's daily `precipitation_sum` (mm, rain+showers+snowfall
water-equivalent - added to `OPEN_METEO_FORECAST_URL`'s `daily=` list
specifically for this feature) - `weather_data._precip_quality_tier`:

| Range | Tier |
|---|---|
| < 0.2mm | Droog → **Goed** |
| 0.2 to 5mm | Lichte neerslag → Matig |
| 5 to 15mm | Neerslag → Slecht |
| ≥ 15mm | Zware neerslag → Zeer slecht |

The 0.2mm cutoff doubles as the "is rain expected" gate for the mm text
(`DayForecast.rain_expected`) - a single definition of "raining" shared by
both features on the card, rather than two.

#### Combining into one 4-tier scale

A fresh, small scale - deliberately not `COMBINED_TIERS` (that's AQI/
pollen's own 5-tier scale, a different concern):

```python
FORECAST_QUALITY_TIERS = ["Goed", "Matig", "Slecht", "Zeer slecht"]
quality_tier_index = max(_temp_quality_tier(high), _precip_quality_tier(precip_mm))
```

`widgets/forecast.py` maps the result straight to the card's outline color
(green/yellow/orange/red - `PALETTE.forecast_border_good/fair/poor/bad`) -
a colored **border**, not a filled background, so the card interior stays
white and nothing about existing icon/text rendering had to change.

#### Worked examples

| High | Precip | Tier | Why |
|---|---|---|---|
| 20°C (Goed) | 0mm (Goed) | Goed | both inputs agree |
| 5°C (Matig) | 0mm (Goed) | Matig | dry but cold - still just "fair" |
| 28°C (Slecht) | 0mm (Goed) | Slecht | heat is the bigger driver |
| 20°C (Goed) | 20mm (Zeer slecht) | Zeer slecht | heavy rain is the bigger driver |
| -2°C (Slecht) | 20mm (Zeer slecht) | Zeer slecht | both inputs bad, worse of the two wins |

See `scripts/test_forecast_quality_scenarios.py` for these and more as
executable, deterministic assertions (every tier, both boundary edges
exactly, the two inputs disagreeing in opposite directions, and the
mm-text on/off gate) - live weather won't reliably hit an exact boundary
value or a rare combination (a heatwave day that's also drenched) on any
given test run.

The mm text's font shrinks to fit the card width if needed
(`widgets/forecast.py::_fit_font`, same shrink-to-fit approach
`WeatherCanvas._fit_font` in `canvas.py` already uses for compact-mode
data-point labels) - narrower cards at a higher `forecast_days` setting
would otherwise let a longer amount like "0.6mm" overflow the border.

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
| `/wifi` | Add/edit (password and/or SSID rename)/remove saved WiFi networks (never auto-removes existing ones) |
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

The app is metric-only by design (°C, m/s, km, mm/cm) - there is no
`units` setting. Imperial/standard (Kelvin) support existed briefly and
was removed 2026-08-11 after testing surfaced real chart-axis bugs
specific to those unit systems (`TODO.md`), rather than being fixed.

| Field | Default | Effect |
|---|---|---|
| `latitude`, `longitude` | Sittard, NL (51.0004365, 5.8993687) | Location passed to every Open-Meteo/Nominatim request, and used to resolve/cache the nearest RIVM station for "Kwaliteit & Pollen" (see above - re-resolved automatically when this changes). The header's location name is Dutch inside the Netherlands, English everywhere else (`weather_data.get_nearest_location_name`) |
| `timezone` | `"Europe/Amsterdam"` | IANA tz name; only used as a fallback if Open-Meteo's response omits its own `timezone` field |
| `time_format` | `"24h"` | `"24h"` \| `"12h"` - hour labels on the chart and the header's "Laatste update" time |
| `forecast_days` | `7` | Number of forecast cards shown in the bottom row (today is excluded from the row itself; `fetch_snapshot` internally requests `forecast_days + 1` days from Open-Meteo) |
| `graph_icon_step` | `2` | Draw an hourly weather icon (and x-axis tick/label) every Nth hour on the chart, instead of every hour |
| `show_moon_phase` | `False` | Whether forecast cards show the moon-phase icon + illumination % (bottom-left of each card) |
| `background_color` | `"#ffffff"` | Canvas background (hex) |
| `text_color` | `"#000000"` | Default text/line color (hex) |
| `inky_saturation` | `0.0` | 0.0-1.0 blend between the panel's desaturated and fully-saturated native palettes (see [Color palette](#color-palette-widgetspalettepy) below) - changing it automatically re-syncs every widget color (`widgets.palette.PALETTE`), not just the final quantization step |
| `font_family` | `"bitter"` | `"bitter"` \| `"jost"` - see `widgets/icons.py`'s `FONT_FAMILIES`. Bitter is the default after a real-hardware comparison (2026-08-11, see `docs/changes.md`); Jost remains available. Local-only override for testing new candidates without a web UI entry: `main.py --font-family` |
| `min_update_interval_minutes` | `0` | Minimum minutes between checks, on top of the fixed 10-minute systemd timer cadence - `0` means no extra throttling. See [Display refresh cadence](#display-refresh-cadence-display_freshnesspy) above |
| `force_refresh_max_stale_minutes` | `60` | How long the physical display can go unrefreshed while the main icon/temperature are unchanged before a refresh is forced anyway. See [Display refresh cadence](#display-refresh-cadence-display_freshnesspy) above |

## Via CLI flags (`main.py`, local/dev use only)

Not available on the deployed Pi (the systemd service invokes `main.py` with
no arguments) - only relevant when running `python main.py` by hand.

| Flag | Values | Effect |
|---|---|---|
| `--mock-output <path>` | any file path | Render to a PNG via `display/mock_driver.py` instead of driving real Inky hardware |
| `--screen-mode` | `original` \| `gridlines` \| `compact` | Override the button-selected mode (`display_mode.get_mode()`) for one render |
| `--font-family` | `bitter` \| `jost` | Override `config.font_family` for one render, without touching the saved setting - useful for trying a new font candidate locally |

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

Not a "setting" in the adjustable-knob sense, but a would-be sharp edge
that's now handled automatically: every widget color comes from the
shared `widgets.palette.PALETTE` singleton (`PALETTE.uv_low`,
`PALETTE.aqi_band_high`, wind compass colors, etc.), computed at a given
`saturation`. `PALETTE.set_saturation(config.inky_saturation)` is called
at the top of both of the app's actual rendering entry points
(`canvas.py`'s `WeatherCanvas.__init__`, `setup_screen.py`'s
`render_setup_screen`), so every render keeps `PALETTE` in sync with
whatever `inky_saturation` that particular `DisplayConfig` specifies -
authored colors always stay exact panel-palette matches, never silently
drifting into dithered speckle even if `inky_saturation` is changed via
the web UI. See `scripts/test_palette_sync.py` for deterministic
coverage, `scripts/panel_sim.py` (preview at the actual driven
saturation), and `scripts/color_options.py` (side-by-side comparison at
other saturations).
