# Changes Log

Numbered list of InkyPiZero's larger changes, each tagged **Active**,
**Outdated** (superseded by a later entry - named), or **Rejected** (tried,
never merged or later fully reverted). Minor tweaks/typo fixes aren't listed
individually.

Append a new entry whenever a major change lands; when it supersedes an
earlier one, go back and mark that entry outdated rather than leaving it
looking current - see the standing rule in [CLAUDE.md](../CLAUDE.md).

---

### 1. Initial port from Flask/Chromium InkyPi to a standalone Pillow renderer
`3084635` (2026-08-05, initial commit)

Fresh-history split from `fatihak/InkyPi`'s weather plugin (via an
intermediate `Dorus-Weather/InkyPi` fork). Replaces the upstream Flask web
app + plugin system + Chromium/CSS rendering with a standalone Pillow-native
renderer run via a systemd **timer** (not a persistent service) - targeted
at hardware too weak to run a headless browser (Pi Zero W). Established
`canvas.py`, `widgets/`, `TODO.md`, the initial (Flaticon-sourced) icon set.

**Active** - the architectural basis of everything else in this log.

### 2. Replace Flaticon icons with an erikflowers/weather-icons-derived set
`a54c67f` / PR #1 merge `15fea80`

Original icons were individually sourced from different Flaticon authors
with wildly inconsistent internal padding (content height 352-468px within a
512x512 canvas). Replaced with a coherent set generated from
erikflowers/weather-icons SVGs via a new dev-only `scripts/generate_icons.py`
(`resvg-py`).

**Active** - this generation pipeline still produces every icon asset today,
though its *content* (colors, composites) was heavily iterated on later
(entries 6, 9, 13).

### 3. Fresh-install hardware/SPI/I2C fixes
`33831ff`, `b70643a`

Three first-boot failures fixed: missing `libopenblas0` (numpy import
chain), I2C disabled (Inky EEPROM autodetect needs it), and the default
SPI0 chip-select overlay conflicting with `inky`'s own manual GPIO
chip-select handling (`dtoverlay=spi0-0cs` added).

**Active** - foundational install fix, untouched since.

### 4. Chart-strip icon darkening/solidify experiment
`20f2849`…`60a8b93` → reverted by `0d6c004`

Tried darkening chart-strip icons and flood-filling hollow icon interiors
solid. Explicitly reverted same-session ("the darkening/hole-filling/
moon-resizing experiment... didn't land well").

**Rejected.** Direct precursor to the larger, similarly-rejected
display-opt/color-tour experiment (entry 9) - the "flood-fill hollow icons
solid" idea was tried twice, rejected both times.

### 5. Background color + icon overview tooling
`1a9a176`, `e18f194`, `5a9c8c5`

Background changed cream → white; added a dev-only icon contact-sheet
script.

**Active.**

### 6. Icon color Proposal A → Proposal B
`ba30a6f` (Proposal A: unified blue clouds/rain/snow, smaller moon),
`5ae9ada` (Proposal B: Pimoroni-native ACeP palette)

Proposal B recolored icons to the Inky panel's actual 7-color ACeP ink
values instead of arbitrary hex, to minimize dithering.

**Outdated** - formalized by entry 12 (`widgets/palette.py`), which
centralizes exactly this approach as the ongoing source of truth. Proposal
A's "unified blue clouds" idea persisted into later work.

### 7. Humidity-drop band calculation
`8af8564` → `99cd830`

Split humidity into 6 equal drop-fill bands; `99cd830` replaced the initial
float-division calc with explicit threshold pairs to avoid rounding edge
cases.

**Active** (`99cd830` is the current form).

### 8. Button-triggered features: shutdown → unified button/screen-mode listener
`5348bf5` (shutdown button, `shutdown_button.py`, GPIO5,
`pi-weather-shutdown.service`) → renamed/generalized by `8541fb2`
(`button_listener.py`, `display_mode.py`, `pi-weather-buttons.service`) →
extended by `f40c4ce` (button D) → reconciled by `9a8592b`

**Outdated** - `shutdown_button.py`/`pi-weather-shutdown.service` superseded
by `button_listener.py`/`display_mode.py`/`pi-weather-buttons.service`
(current files, entry 14). The shutdown behavior itself (button A, GPIO5,
blank+poweroff) is still active, just folded into the unified listener -
see [settings.md](./settings.md).

### 9. "display-opt" branch: icon solidify + 3-step color tour
`06107ce`, `dec1231` (solidify + chart-icon size bumps 20→24→30px) →
`a284801`/`c567947` (revert/re-revert 022d color) → `b94da24`/`b4b43d2`/
`643e76f` (color tour 1-3) → **explicitly reverted by `37752ae`**
("Revert display-opt + color tour back to pre-display-opt state" - verified
byte-identical to pre-experiment tree)

**Rejected**, fully. The icon-size increase alone was judged worth keeping
and was reapplied standalone immediately after (`ac3d227`, entry 10) - only
the solidify treatment and the color-tour experiments were thrown out.

### 10. Chart-strip icon size + outline-thickening pipeline
`ac3d227` (icon size 20→30px, clean reapply post-revert), `31338ce`
(`thicken_icon()` - alpha-dilation outline thickening, not fill), `bd3dc02`
(half-strength default), `10cd24d` (extended to forecast cards), `a615148`
(fix contaminated edge-color sampling)

**Active.** This "outline dilation" approach is what stuck, as opposed to
the rejected flood-fill/solidify approach (entries 4, 9). Extended by entry
13 (composite icons) and nearly generalized app-wide by the rejected
entry 17.

### 11. Chart polish: dashed min/max lines, UV/AQI text, margins, label positions
`0eb0f58`, `bc70264`, `8ba833b`, `a16483c`, `09f1fce`, `d4127b6`, `420263d`,
`5508890`, `b30a68f`, `e9084e4`, `f901ae8`, `90531d0`, `ce9363b` (and others)

Incremental refinements to the "original" chart style: UV index rounded +
rated in words, AQI shows text rating only, 2mm display-edge margin, fixed
rain-axis label clipping on heavy-rain days (found via Bangkok monsoon
testing), fixed min-line label colliding with x-axis hour labels below 0°,
"Regen"/"Regen [mm]" vertical axis label introduced and repositioned.

**Active**, except the hardcoded **"Regen"/"Regen [mm]" label** itself,
**outdated - superseded by entry 20** (dynamic rain/hail/snow/dry label).

### 12. `widgets/palette.py`: centralized panel-matched color palette
`36bd167` (branch `panel-color-optimize`) - every widget color previously an
"arbitrary RGB guess" that looked fine in local `--mock-output` renders
(which skip quantization) but dithered into speckle on real hardware.
Centralizes every color role as an exact match to the Inky panel's real ink
colors at a configurable `inky_saturation`. New dev tools:
`scripts/panel_sim.py` (simulates real quantize+dither locally),
`scripts/color_options.py` (saturation comparison). Follow-ups: `817fd1d`
(fix humidity-drop icons dithering near-invisible), `eead696` (final choice:
desaturated/`saturation=0.0` preset, pure-primaries, confirmed live on
hardware over the initially-tried "vivid" 1.0 preset).

**Active, foundational** - current color source of truth app-wide. See
[Color palette decision](../CLAUDE.md) and `docs/settings.md`'s note on
keeping `inky_saturation` and `PALETTE`'s hardcoded singleton in sync.

### 13. Half-cloudy composite icons (`022d`/`022n`, two-tone sun/moon + cloud)
`88e8b0a` (two-tone composite + multi-color-aware `thicken_icon()`),
`4f822dc` → `f6b0bf0` (solid-fill the cloud only, keep sun/moon hollow),
`bfb4ce3` (render each layer directly at final size - fixes blur), `15c52f1`
(extra boldening pass on the sun/moon ring), `54532b0` (fix WMO code 2 using
a blue-only icon instead of the composite), `b1197bd` (extra boldening pass
on the cloud's bottom line)

**Active** - current design of the `022d`/`022n` composites. Its
composite-specific `thicken_icon()` boldening passes survived because entry
17 (which would have removed them in favor of an app-wide default) was
rejected.

### 14. Second/third screen layouts: "gridlines" and "compact" modes
Gridlines (button C) - `8541fb2`: 10°C uniform reference grid replacing the
day's actual min/max dashed lines. Compact (button D) - `f40c4ce`: 4 details
instead of 6 (drops visibility/pressure), 2x2 grid, bigger fonts; three
interchangeable sub-layouts exist (`compact_style`: `icon_left`/
`icon_above`/`icon_above_row`), `icon_left` wired as the de facto default
with no follow-up commit revisiting the choice. Reconciliation merges:
`782b12f`, `ec59f89`, `664b10d`, `9a8592b` (unifies both independently-built
button systems into one: A=shutdown, B=original, C=gridlines, D=compact).
`4100ed5` - **gridlines made the default mode** (`DEFAULT_MODE`). `2feb3ca`
- per-line gridline labels + margin/collision fixes. `5fc98c4` - compact
mode adopts the gridlines chart style too. `03518a6` - gridline label
column-alignment fix.

**Active** - all three modes (`original`/`gridlines`/`compact`) coexist
today, all reachable via their buttons; `gridlines` is the default for fresh
installs. See [settings.md](./settings.md) for the full mode/button table.
**Outdated in one respect**: `compact_style`'s three sub-layouts and the
"no follow-up commit revisiting the choice" gap are resolved by entry 27 -
`icon_left` is now the only implementation, `compact_style` itself is gone.

### 15. Chart axis tweaks: unit-in-label, hour ticks, date-change line
`dbb2466` (branch `chart-axis-tweaks`) - axis-extreme labels read "28°C"/
"0°C" directly (dropped the separate always-present vertical "C" unit
label), hour tick marks, a vertical dotted day-boundary line (new
`HourPoint.is_day_start`). `f384451` - aligned the date line to 00:00's own
tick instead of the column edge. Merged into both gridlines and compact via
`ec59f89`/`664b10d`.

**Active.**

### 16. Nearest-color quantization pipeline (`display/quantize.py`)
`78a5018` (branch `icon-nearest-color-quantize`) - `inky`'s default
Floyd-Steinberg dithering is built for photos and turns thin line art
(chart lines, icon outlines) into speckle/gaps even at an exact color match.
Switching to plain nearest-color quantization fixes that but exposes a
*worse* problem: antialiased black-on-white edges blend through neutral
gray, and on this specific 7-color palette, gray's *nearest* color by
Euclidean RGB distance is actually **orange** (more central in the color
cube than any near-corner color) - a systematic orange fringe resulted.
`harden_neutral_pixels()` snaps near-gray antialiased pixels to pure
black/white before quantizing to remove the ambiguity. `display/
inky_driver.py` now pre-quantizes to `"P"` mode so `inky`'s own internal
Floyd-Steinberg is skipped entirely.

**Active** - current hardware output pipeline, confirmed live. Its own
commit message credits this fix with likely making entry 17 unnecessary.

### 17. "icon-hardening" branch - app-wide icon anti-aliasing hardening
Orphan commit `2e07b19` (2026-08-08, branch `icon-hardening`, since
deleted - verified not reachable from any current branch)

Would have generalized the composite-specific boldening passes (entry 13)
into an app-wide default (`ICON_THICKEN_STRENGTH` 0.5→1.0). Noted an
unsolved residual issue even with the fix: black icons (fog/storm) still
speckle more than colored ones since neutral gray sits equidistant from all
7 palette colors.

**Rejected** - never merged, branch deleted. Superseded in practice by entry
16's quantization-level fix, which produced a cleaner result at the source
instead. Because this was rejected, the composite-specific thickening
passes from entry 13 remain in `generate_icons.py` today, unremoved.

### 18. Remove chart temperature fill shading, thicken the line
`c531ebb` (branch `chart-noshade-thicker-line`) - the translucent fill under
the temp curve always dithered into visible stipple on real hardware (alpha
compositing against white produces an off-palette color regardless of the
authored color); dropped entirely, line width 4→5px to compensate. Removed
now-dead `_positive_fill_segments()` and `PALETTE.chart_fill`.

**Active** - supersedes an earlier same-idea "lighten the fill" attempt
(`629696f`); the fill concept is gone from the chart entirely now.

### 19. Small polish pass + 14-location regression testing rule
`44e8af7` (14-location consistency test established as a standing testing
rule), `1bafb51` (chart label fonts 12→14px, rain axis label becomes "Regen
[mm]"/"[in]", "UV-index" → "UV-index 1-12", AQI text-only), `0a18284`
(wider chart, bigger x-axis hour-label font)

**Active**, except the **"Regen [mm]" label** from `1bafb51`, **outdated -
superseded by entry 20**.

### 20. Dynamic precipitation axis label (rain/hail/snow/dry)
`1e91559` (branch `precip-label`), merged to main at `903fdc6`

The hardcoded "Regen [mm]" label (entries 11, 19) is replaced with real
classification in `weather_data.py`: snow-coded hours plot snowfall in cm
("Sneeuw [cm]", new `snowfall` Open-Meteo hourly variable), thunderstorm-
with-hail codes (96/99) relabel to "Hagel [mm]" (still plots total
precipitation - Open-Meteo has no separate hail-depth variable), an
all-zero 24h window shows "Droog" with no unit.

**Active** - current state of the precipitation axis label. Verified against
both live data (14-location test) and deterministic synthetic fixtures for
all four branches (`scripts/test_precip_scenarios.py`, since live weather
can't reliably guarantee a hailstorm on any given test run).

### 21. WiFi provisioning + always-on settings web UI
Branch `wifi-setup-webui`

The project's first departure from "no web UI, no long-running service
besides the button listener" (entry 1): a new always-on Flask service
(`pi-weather-web.service`, `web_app.py` + `web/`) runs completely
independently of the render timer, exposing every `config.py` field as a
form (persisted to `/var/lib/pi-weather-display/settings.json` via new
`settings_store.py`, overlaid on `DisplayConfig`'s dataclass defaults - the
only change to existing code is `main.py`'s `DisplayConfig()` ->
`settings_store.load_config()`), WiFi network management (add/edit/remove,
`wifi_manager.py`), and a `/shutdown` route reusing
`button_listener.blank_and_shutdown()`.

WiFi provisioning went through a real mid-flight architecture change: the
first approach (NetworkManager's own native hotspot mode) reproducibly
failed on the deployed Pi Zero W across three separate live tests, all with
the same NetworkManager-internal "Hotspot network creation took too long" /
supplicant-timeout error - confirmed to be NetworkManager's own AP
implementation (which drives WPA-PSK AP mode through `wpa_supplicant`
rather than a dedicated AP daemon), not a hardware limitation (the driver
correctly advertises AP-mode support). Switched to **hostapd** + a
dedicated dnsmasq instance instead (two new on-demand, never-boot-enabled
units, `pi-weather-hostapd.service`/`pi-weather-ap-dnsmasq.service`,
started/stopped only by `wifi_manager.py`) - the standard, purpose-built
approach for exactly this on Raspberry Pi hardware. Verified live
end-to-end afterward: AP up in ~14s, the e-paper setup screen
(`setup_screen.py`) genuinely rendered, clean reconnect back to the station
network, with the render timer and button listener completely undisturbed
throughout every test. See [networking.md](./networking.md) for the full
design and evidence.

Also confirmed empirically (not assumed) that netplan, also present on this
image, doesn't interfere with `nmcli`-managed profiles - it only tracks the
specific connections it created at image-build time.

**Active** - current architecture. Known deferred scope, tracked in
`TODO.md`: no SSID rename (remove + re-add instead), no periodic
runtime reconnect-check (the connectivity check only runs at
`pi-weather-web.service` startup, not continuously), no real captive-portal
DNS redirect on the setup AP, no authentication anywhere (matches button
A's existing unauthenticated-shutdown precedent; trusted-LAN-only by
design).

---

### 22. Pollen data merged into AQI as one combined "Kwaliteit & Pollen" reading
Branch `pollen-hayfever-detail`

Started as a standalone pollen/hay-fever (Hooikoorts) data point, sourced
from the same Open-Meteo air-quality endpoint already used for UV/AQI (6
hourly species: alder, birch, grass, mugwort, olive, ragweed - Europe-only,
null outside each species' active season), with its own flower icon and a
6th-cell swap with visibility. Comparing live output against
pollennieuws.nl surfaced two real correctness bugs in that version, fixed
along the way and still load-bearing in the final design: (1) same-tier
ties were broken by dict iteration order, so an always-0.0 off-season
species (alder, in August) beat a genuinely active one (grass) just by
being listed first in `POLLEN_SPECIES_NL` - fixed by breaking ties on
concentration normalized against each species' own threshold group
instead; (2) classification originally used the exact current-hour
reading (matching UV/AQI/humidity's pattern), but pollen swings hard hour
to hour - Sittard's grass count ranged 4.4-9.8 grains/m3 across one day,
and the exact hour checked happened to sit at a local dip. Switched to
each species' **peak value anywhere in the current calendar day**
(`weather_data._value_max_today`), a deliberate exception to the
current-hour pattern AQI/UV/humidity still use.

**Then changed direction**: rather than keep pollen as a separate,
frequently-absent 6th/7th cell, it's merged into the existing AQI data
point - one combined reading, using the AQI gauge icon, labelled
"Kwaliteit & Pollen", showing the **worse of** AQI and pollen. This
removes the earlier version's visibility-swap mechanic and compact mode's
variable 4-or-5-cell layout entirely - visibility is unconditional again,
and compact mode is always exactly 4 cells, matching the app's original
(pre-pollen) shape.

`weather_data._combine_aqi_pollen_tier` maps both inputs onto one new
4-tier scale, `COMBINED_TIERS = ["Goed", "Matig", "Slecht", "Zeer
slecht"]` - a fresh scale (confirmed with the user, picked over reusing
either AQI's native 6 tiers or pollen's native 4 outright) chosen so both
inputs can reach every tier symmetrically: AQI's 6 tiers fold on via
`_AQI_TIER_TO_COMBINED = [0, 0, 1, 2, 3, 3]`, pollen's 4 tiers already
match 1:1. `get_combined_rotation` reuses `render_aqi_gauge`'s existing 4
color bands unchanged, positioning the needle by combined tier index
instead of a literal 0-100 AQI value, so the needle stays honest even when
pollen (not AQI) is the worse contributor. The driving pollen species is
still named as a second word (e.g. "Zeer slecht Berk") when pollen's tier
is at or above AQI's contribution; when AQI alone is the worse or equal
factor, no species is shown. `render_pollen_icon` (the standalone flower
icon from the earlier version) and `get_pollen_color` were removed as
dead code once nothing called them anymore.

The longer "Kwaliteit & Pollen" label didn't fit compact mode's fixed-size
fonts at the old label length ("Luchtkwaliteit") - added `WeatherCanvas.
_fit_font`, a small shrink-to-fit-width helper (steps font size down in
2px increments until `font.getlength(text) <= max_width`), applied to
both label and value text in both compact styles rather than special-
casing this one string.

`scripts/test_pollen_scenarios.py` (mirrors entry 20's precip-scenario
script) fakes the air-quality fetch with crafted hourly pollen *and*
`european_aqi` values, covering: every pollen tier alone, a tree-vs-grass
tie-break, the zero-vs-active species tie regression, the
daily-peak-vs-current-hour regression, AQI alone, AQI-worse-than-pollen
(no species named), pollen-worse-than-AQi (species named), a tied-tier
case, and the neither-available fallback - live weather can't reliably
guarantee season/hemisphere coverage or a specific AQI+pollen combination
on any given run.

**Then simplified the driving-cause label further**: the exact species
name (e.g. "Berk") was too granular for the small icon label, so
`_pollen_category_nl` summarizes it to one of 3 broad categories instead -
**Boom** (alder/birch/olive), **Gras** (grass), or **Ambrosia**
(mugwort/ragweed - named for the more severe weed species, not a literal
per-species mapping), confirmed with the user 2026-08-10.
`_classify_pollen`'s returned key was renamed `species_nl` ->
`category_nl` to match.

**Then refined when the category is shown**: appended after a colon now
("Zeer slecht: Boom" rather than "Zeer slecht Boom" - a new per-data-point
`unit_separator` field on `_data_point_value_text`, every other data point
still uses a plain space), and only when pollen is genuinely elevated
(`pollen_tier_index > 0`) as well as at-or-above AQI's contribution - a
tied "Goed" (pollen merely Laag) no longer names a category, since "Goed"
alone already says everything's fine. Confirmed with the user 2026-08-10.

**Outdated in one respect**: the AQI *source* (Open-Meteo `european_aqi`)
and the 4-tier `COMBINED_TIERS`/`_AQI_TIER_TO_COMBINED` fold described
above are superseded by entry 32 (RIVM/luchtmeetnet.nl, 5-tier scale). The
combined-data-point architecture itself - one "Kwaliteit & Pollen" cell,
worst-of-both-inputs, the cause-label rules, `_fit_font`, pollen's own
classification - is unchanged and still current. Known permanent
limitations, tracked in `TODO.md`: pollen's contribution is Europe-only/
seasonal (an Open-Meteo data limitation, not a bug, falls back to AQI
alone or "N/A"), and Open-Meteo/CAMS models fewer herb/weed species than
Dutch pollen services track (confirmed against pollennieuws.nl's broader
"Kruiden" category).

---

### 23. Skip unchanged display refreshes, force one hourly
Branch `skip-unchanged-refresh`

`pi-weather-display.timer` still fires every 10 minutes and `main.py`
still fetches fresh data every tick, but the physical panel is only
actually refreshed - the flash, and the real e-paper wear cycle - when
it's worth it: the main current-conditions icon or the big temperature
number changed since the last refresh, or an hour has passed regardless
(so slower-moving details like the forecast cards, hourly chart, and
"Laatste update" timestamp don't go stale indefinitely during a long
stretch of unchanged weather).

New `display_freshness.py` mirrors `display_mode.py`'s established
"small state file under `/var/lib/pi-weather-display/`" pattern
(`main.py` is a one-shot job with no memory between runs): persists the
last-shown icon key/temperature/timestamp, and a separate one-shot
sentinel file for forced refreshes. `main.py` was split so the freshness
decision happens right after fetch, *before* the costlier canvas render
step - a skipped tick avoids both the Pillow render and the display
write, not just the write. `--mock-output` (local testing/preview)
bypasses the check entirely and always renders.

`button_listener.py`'s `switch_mode()` and `web/routes.py`'s
`_trigger_rerender()` (the single shared trigger for every settings-save/
WiFi-change re-render in the web UI) both write the forced-refresh
sentinel immediately before their existing `systemctl start
pi-weather-display.service` call - a user pressing a screen-mode button
or saving a setting always sees the change immediately, never silently
skipped because the icon/temperature happened to be unchanged.

New `scripts/test_display_freshness.py` covers the decision logic
directly against a temp state directory (first run, unchanged within/past
the hour, changed icon, changed temp, a skipped tick not resetting the
timer, a corrupt state file, the forced-refresh sentinel) - no network or
hardware needed, matching this repo's established crafted-fixture testing
convention.

**Active** - current design. Deliberate tradeoff, tracked in `TODO.md`:
other data points can go up to an hour stale on the physical display even
though the underlying fetch happens every 10 minutes, if the icon/temp
both hold steady. The hardcoded 10-minute/1-hour cadence this entry
shipped with is superseded by entry 24 - the hour ceiling is now a real
setting (`force_refresh_max_stale_minutes`).

### 24. Configurable refresh cadence
Branch `configurable-refresh-cadence`

Replaces the dead `config.py` field `refresh_interval_seconds` (never
read anywhere) with two real, web-UI-exposed settings:
`min_update_interval_minutes` (default `0`) and
`force_refresh_max_stale_minutes` (default `60`, replacing entry 23's
hardcoded `display_freshness.MAX_STALE`).

The systemd timer's own 10-minute tick stays fixed and root-owned on
purpose - rewriting it from the web app would need root and risks
breaking the render pipeline or `install.sh`'s "safe to rerun any time"
idempotency (the same tradeoff already weighed and deferred for the WiFi
provisioning feature, entry 21). Instead, `min_update_interval_minutes`
is a software-only throttle: `main.py` checks it first, before even
fetching weather data, and skips the tick entirely if not enough time
has passed. `force_refresh_max_stale_minutes` slots into the same
`should_update_display` check entry 23 introduced, just parameterized
instead of hardcoded.

`display_freshness.py`'s state file gained a `last_check_time` field
alongside the existing icon/temp/`last_display_time` ones; `record_check`/
`record_display` now read-modify-write so recording one throttle's state
never clobbers the other's. A forced refresh (button press, settings
save) bypasses both throttles, matching entry 23's existing guarantee
that user-triggered changes always show up immediately.

New tests added to `scripts/test_display_freshness.py`: `should_run_check`
first-run/within-interval/past-interval behavior, and a read-modify-write
check confirming `record_check` doesn't clobber `record_display`'s state
(and vice versa).

**Active** - supersedes `refresh_interval_seconds`, entry 23's hardcoded
`MAX_STALE`.

### 25. Metric-only: remove imperial/standard unit support
Branch `metric-only-units`

Removes `config.py`'s `units` field and every `imperial`/`standard`
(Kelvin) code path - the app is metric-only now (°C, m/s, km, mm/cm).
Tested via `--mock-output` in all three screen modes 2026-08-11: real
chart-axis bugs turned up specific to those unit systems (Kelvin's
0-310K range made gridlines/compact mode nearly unreadable - a fixed
10-unit gridline step over that span produced ~30 overlapping labels;
Fahrenheit's 0-floored axis wasted most of the chart's vertical space).
Both were caused by axis-scaling logic (`widgets/chart.py`) calibrated
for Celsius's small near-zero range, not by the unit conversions
themselves - rather than generalizing the axis logic to handle
arbitrary units, the simpler fix was removing the units this app was
never really designed to support well in the first place.

`weather_data.py` lost its `UNITS`/`OPEN_METEO_UNIT_PARAMS` dicts, the
`get_wind_speed_ms()` imperial conversion, and every `if units ==
"standard"`/`"imperial"` branch (Kelvin's `+273.15` offset, Fahrenheit's
visibility-in-miles/inch precipitation units) - `config.units` is gone
from `config.py`, `settings_store.py`, `web/routes.py`'s form parsing,
and the settings page's "Eenheden" dropdown. `canvas.py`/
`widgets/chart.py` also lost their `!= "K"` conditionals (dead now that
Kelvin can't occur) in favor of a plain `°C` suffix everywhere.

**Active** - current design, metric-only. Entry 20's rain/hail/snow axis-
label classification itself is unaffected; only its imperial "in" variant
(never separately called out there) is gone - `rain_unit`/`snow_unit` are
always "mm"/"cm" now.

### 26. Wire `PALETTE` to `config.inky_saturation`
Branch `palette-saturation-sync`

Closes a long-standing TODO.md item: `widgets.palette.PALETTE` (every
widget's color source - `PALETTE.uv_low`, `PALETTE.aqi_band_high`, wind
compass colors, etc.) was a module-level singleton computed once at
import time from a hardcoded `saturation=0.0`, completely disconnected
from `DisplayConfig.inky_saturation` - a genuinely user-changeable field,
exposed and persisted via the web UI's settings form since entry 21. The
*final* display step already read `config.inky_saturation` correctly and
dynamically; only the palette-color side didn't. Had a user ever changed
the setting away from `0.0`, every "exact panel match" color would have
silently stopped being exact, reintroducing the dithered-speckle problem
this whole `PALETTE` system exists to prevent (entries 6/9 - see
`color_palette_decision`/`quantization_pipeline_decision` history).

The fix mechanism already existed and was already correct -
`Palette.set_saturation()` mutates the shared singleton in place, but was
only ever called from `scripts/color_options.py`, a dev-only comparison
tool. Rather than scatter a sync call across every current and future
render call site, it's now called once at the top of each of the app's
two actual rendering entry points - `canvas.py`'s `WeatherCanvas.__init__`
and `setup_screen.py`'s `render_setup_screen` - so every caller
(`main.py`, all three standing test scripts, `web_app.py`'s WiFi-AP setup
screen) gets it automatically with no changes of their own needed.

New `scripts/test_palette_sync.py` asserts `PALETTE.saturation` actually
moves to match a non-default config after constructing each entry point,
including re-syncing correctly across a second construction with a
*different* saturation (the real bug scenario: `main.py` loads whatever
config is currently saved, fresh, on every one-shot run). Verified beyond
the unit test too - rendered at `inky_saturation=0.5` and confirmed via
`scripts/panel_sim.py` that colors stayed flat/on-palette, not speckled.

**Active** - current design. No remaining known gaps for this specific
item.

### 27. Commit to icon_left, remove compact_style's other two sub-layouts
Branch `commit-compact-style-icon-left`

Closes entry 14's leftover decision: "compact" screen mode had three
interchangeable data-point-cell arrangements (`compact_style`:
`icon_left`/`icon_above`/`icon_above_row`) built for comparison, but only
reachable via `main.py`'s `--compact-style` CLI flag - no button or web
UI ever exposed the other two, `icon_left` had been the de facto live
default since day one. Rendered fresh side-by-side comparisons of all
three (2026-08-11): `icon_above` left an awkward whitespace gap between
icon and text in each 2x2 cell; `icon_above_row`'s single-row layout was
decent but didn't clearly beat `icon_left`, and weakened the visual
grouping between an icon and its text. Committed to `icon_left`.

Removed: `canvas.py`'s `compact_style` parameter and
`_draw_compact_cell_icon_above` (the remaining
`_draw_compact_cell_icon_left` renamed to `_draw_compact_cell`, now the
only implementation); `main.py`'s `--compact-style` flag and its
threading through `render_canvas()`; `layout.py`'s now-dead
`data_point_cell_1x4` (only `icon_above_row` used it).

**Active** - current design. `compact_style` no longer exists as a
concept anywhere in the codebase.

### 28. Text-rendering fix investigation - every alternative rejected, keeping Jost
Branches `text-rendering-fontmode-prototype`,
`text-rendering-bitmap-font-prototype`, `text-rendering-font-candidates`
(none merged)

Closed out the "bold text ~18-24px shows stair-stepped curves on real
hardware" TODO item (entry-worthy on its own, given the amount of real
testing involved, even though the conclusion is "no change"). Three
alternatives prototyped and pushed to the *actual* Inky panel - not just
digital previews, this project's own precedent (the earlier
`supersampled-text-compare` experiment) already showed a digital
comparison can look better while looking worse on real e-paper:

1. **PIL's `fontmode="1"` native monochrome rasterization** - zero new
   dependencies, confirmed empirically to toggle per-call with no side
   effects. **Rejected** - not better than normal antialiased+hardened
   rendering.
2. **True bitmap fonts** - Spleen and Terminus (both BDF, both
   discovered/verified via their actual license files rather than
   assumed), including a `thicken_icon()`-style alpha-dilated fake-bold
   for Spleen's single weight. Also corrected a wrong assumption in the
   original plan: `BdfFontFile.to_imagefont()` doesn't exist in this
   repo's pinned Pillow (12.1.1) - the real path is `BdfFontFile.save()`
   + `ImageFont.load()`, confirmed by introspecting the actual class.
   **Rejected**.
3. **Switching TrueType fonts entirely** - dropped in the original
   research for lack of a candidate, reopened after researching what's
   actually recommended for e-ink displays specifically (not general
   ebook-reading fonts, a different problem - those solve grayscale
   body-text legibility at reader-chosen sizes). Literata (Google Play
   Books' serif) and League Spartan (a bold geometric sans specifically
   singled out for e-ink use elsewhere, and a closer stylistic match to
   this app's short bold labels). Along the way, corrected another wrong
   assumption (an initial web-search-sourced claim that Literata is
   unhinted) by inspecting the actual TTF `fpgm` table directly - it
   isn't. That same inspection found `Jost-SemiBold.ttf`'s `fpgm` table
   is 0 bytes, i.e. **Jost itself has no real hinting instructions and
   never has** - relies entirely on FreeType's generic autohinter. League
   Spartan (which does have real hinting) was retested under
   `fontmode="1"` specifically for this reason. **Rejected** - a final
   longer paragraph-scale 2x2 comparison (Jost/League Spartan x Normal/
   `fontmode="1"`) confirmed Jost's current normal rendering still reads
   best.

**Rejected**, all three. `canvas.py` untouched throughout. The three
branches were never merged and remain as a reference trail (full
prototypes, license verifications, and the two corrected-API findings
above) rather than being folded into `main` - see `TODO.md`'s Fonts &
text section and the two plan docs' Status lines for the summary.
**Outdated**: this entry's own "keep Jost" conclusion didn't hold - a
further round of comparisons (entry 29) landed on Bitter after all.

### 29. Adopt Bitter as the default font
Branch `font-family-jost-bitter`

Supersedes entry 28's "keep Jost" conclusion. One more real-hardware
comparison round (Literata, Charter/XCharter, Bitter, Vollkorn, plus a
local-only digital check of Georgia - Bookerly excluded entirely, no
legitimate downloadable source exists for Amazon's Kindle-only font) -
Bitter won this time.

`config.font_family` (`"jost"` | `"bitter"`, `widgets/icons.py`'s
`FONT_FAMILIES`) is now a real, persisted web UI setting (`settings.html`'s
"Weergave" fieldset), default `"bitter"` - not merely a rendering-mode
toggle like entries 24-28's rejected options, an actual typeface swap.
Bitter ships as a single variable-weight file (no separate bold TTF,
confirmed via `font.get_variation_names()`) - `AssetStore.font()` selects
its named `Bold`/`Regular` instance via `set_variation_by_name()`.
`main.py` gained a `--font-family` flag for testing new candidates
locally without touching the saved setting.

Testing across the *full* app (not just isolated "Matig Gras" samples,
the mistake earlier rounds risked) found and fixed a real bug before
shipping Bitter as the default: it's wider than Jost at the same point
size, which clipped the "Kwaliteit & Pollen" label in the 6-cell
(original/gridlines) data-point grid. `_draw_data_points` now uses the
same `_fit_font` width-shrinking helper `_draw_compact_cell` already had
- makes the whole app robust to any future font's different metrics, not
just a one-off patch for Bitter.

Also surfaced (not fixed, not new): a chart gridline-mode max-value-
label-vs-tick-label collision, confirmed via a same-data side-by-side
render to reproduce identically with Jost too - font-independent,
tracked separately in `TODO.md`.

**Active** - current design. `docs/attribution.md` updated (Bitter's
entry promoted from "candidate, not wired in" to the actual default;
Jost's entry now notes it's the selectable alternative).

### 30. Away-mode sweep: font fallback, chart collision, WiFi gaps, shutdown-screen saturation — most recent
Branch `todo-fonts-wifi-fixes`, built autonomously (Mode 3/Away) while
closing out `TODO.md`'s "Fonts & text" and "WiFi & web UI" sections plus
a hardware bug reported the same session.

**Missing font glyph fallback** (`widgets/icons.py`) - Bitter/Jost both
lack CJK/broader coverage (originally surfaced by a real API-sourced
location string, "杉並区, Japan"). New `AssetStore.fallback_font()`/
`draw_text_with_fallback()` fall back per-character to a bundled Noto
Sans JP (Latin/Cyrillic/Greek/CJK) when the active family has no real
glyph for a character, wired into `canvas.py`'s header - the only call
site that draws unpredictable API-sourced text. Glyph-coverage detection
needed a small trick since PIL/FreeType has no direct "has this glyph"
API: a missing codepoint silently resolves to the font's shared
`.notdef` glyph, whose `getbbox()` is a fixed per-font fingerprint (but
differs font to font, so it can't be a hardcoded constant) - comparing a
candidate character's bbox against a guaranteed-absent probe codepoint's
(`U+E000`) bbox reliably infers coverage without a cmap-parsing
dependency. Verified against the original Tokyo case through the real
render + quantization pipeline. Known residual limitation, not solved
here: complex-script languages (Arabic/Thai/Devanagari/Hebrew) would
render correct glyphs but wrong shaping/ordering - Pillow's `text()` has
no bidi/shaping engine.

**Chart gridline-mode max-value label collision** (`widgets/chart.py`) -
the gridline loop previously only skipped a tick at the *exact* same
value as the axis-extreme label; now skips any tick within one measured
label-height (`font_bold.getbbox()`, not a guessed constant) of the
max/min label. Verified against the original Ulaanbaatar repro and the
full 14-location suite.

**WiFi/web UI gaps closed**, all in `wifi_manager.py`/`web_app.py`/
`web/` (see [networking.md](./networking.md) for full design/evidence
on each): SSID rename (`edit_network()` now takes an optional
`new_ssid`, one `nmcli connection modify` call, no remove+re-add;
password field made independently optional too), a periodic background
reconnect check (`web_app.py`'s `_periodic_reconnect_check`, 60s
interval, falls back to the setup AP after 3 consecutive failures -
debounced against momentary router blips), a captive-portal-style
wildcard DNS entry on the setup AP's dnsmasq config (`address=/#/<AP_IP>`
- DNS-only, no OS-level captive-portal popup, HTTPS still fails TLS
validation against the bare IP), and a `WIFI:S:...;T:WPA;P:...;;` QR
code on the setup screen (new `qrcode` dependency, `setup_screen.py`
restructured into a two-column text+QR layout) for one-tap phone
joining alongside the existing text instructions.

**Deliberately not changed**: web UI authentication. Reverses an
explicit, already-documented design decision (trusted-LAN-only threat
model, matches button A's own unauthenticated physical shutdown) - Mode
3 rules require this kind of decision be queued as an explicit yes/no
rather than acted on unilaterally, even though every other item in the
same TODO section was closed out. Still unchecked in `TODO.md`.

**Also fixed, found via a live hardware report**: `button_listener.py`'s
`blank_and_shutdown()` called `InkyDriver()` with no `saturation`
argument, always quantizing at the class's hardcoded default (`0.5`)
instead of the actually-configured `inky_saturation` (default `0.0`) -
now reads `settings_store.load_config().inky_saturation` first, matching
the pattern `main.py`/`web_app.py` already used correctly. Investigated
further, root-cause-with-evidence style: the *reported* symptom (a mild
sprinkling of black dots on the supposedly-blank screen) was NOT
reproduced by rendering a synthetic pure-white image through the same
`quantize_for_panel()` pipeline at either saturation value - both
produced a perfectly uniform single-color output, ruling out the
software pipeline. Left unfixed, tracked in `TODO.md`: very likely a
genuine physical e-paper artifact (incomplete ink-particle clearing from
the previous image, since this screen doesn't do a full clear cycle
first) rather than a software bug - a real hardware-level fix would be
riskier/bigger than this session's scope.

**Active** - current design for every item above except the deliberately
untouched authentication question, still open in `TODO.md`. Deployed to
the real Pi post-review (branch checked out, persistent services
restarted, a forced refresh confirmed "Displaying image to Inky display"
in `journalctl`) - real-hardware confirmation of the shutdown-screen
saturation fix and the QR code's scannability is still outstanding, see
`TODO.md`.

### 31. Translate non-Netherlands location names to English
Branch `todo-fonts-wifi-fixes`

Follow-up to entry 30's font-fallback work: `weather_data.NOMINATIM_REVERSE_URL`
was hardcoded to `accept-language=nl`, so any location outside the
Netherlands got whatever Nominatim's Dutch-translation coverage happened
to produce - often nothing, cascading to the location's own local
name/script (the entry-30 Tokyo case, "杉並区, Japan", was this exact
failure mode). `get_nearest_location_name()` now checks the reverse-geocode
response's `address.country_code` first: for the Netherlands, behavior is
unchanged (Dutch name, one request); for anywhere else, a second request
asks for the English name instead, which has far broader Nominatim
translation coverage - the same Tokyo coordinates now resolve to
"Suginami, Japan". Entry 30's glyph-fallback mechanism stays in place
underneath as a safety net for the rarer case where even an English name
isn't available.

The second request is deliberately spaced 1 second after the first
(`time.sleep(1)`) - Nominatim's usage policy asks for max 1 request/second,
and this is the only call site in the app that ever queries it twice for
a single fetch; production usage (one location, once per 10-minute timer
tick) never approaches this limit on its own. Confirmed the hard way
while testing: firing this same lookup back-to-back across all 14 of the
standing regression suite's locations (up to ~27 requests in a few
seconds) reliably triggers Nominatim's rate limiting regardless of the
1s inter-request spacing - `scripts/test_locations.py` now sleeps 1s
between locations too, purely a test-script concern, not a production
one.

**Active** - current design. Verified directly against the original
Tokyo bug case (confirmed "Suginami, Japan") and Sittard staying Dutch;
a full re-run of the 14-location suite to confirm every location
individually was deferred after repeated testing bursts tripped
Nominatim's rate limit for a while - worth a clean single pass later
once enough time has passed.

### 32. Swap AQI source from Open-Meteo to RIVM/luchtmeetnet.nl, combined scale grows to 5 tiers
Branch `feature/rivm-air-quality`

The "Kwaliteit & Pollen" data point's AQI half (entry 22) came from
Open-Meteo's `european_aqi` - a modeled/interpolated value (Copernicus
CAMS), not a real Dutch measurement. Comparing a live reading against
[longfonds.nl/gezondelucht](https://www.longfonds.nl/gezondelucht) (RIVM's
own ground-station data) surfaced a real gap for the configured location:
Open-Meteo said 37/100 ("Redelijk", displayed as "Goed" under the old
fold), while RIVM's actual nearest station (`NL50003`, Geleen-Asterstraat,
~5.7km away) reported LKI 7 ("Onvoldoende" - much closer to Longfonds'
"Slecht"). Swapped to RIVM's own network via luchtmeetnet.nl's open API
(keyless, 300 requests/5min fair-use, confirmed via its own 429 response).
Pollen stays on Open-Meteo entirely unchanged - RIVM doesn't publish
pollen data.

**Finding the right station** required brute-forcing it: luchtmeetnet has
no geo-filter query param, so `weather_data._resolve_rivm_station` lists
every station (~130 requests total) and picks the nearest one that
actually publishes LKI (not every station does), capped at
`RIVM_MAX_STATION_DISTANCE_KM` (150km) so a non-Dutch location correctly
falls back to no data instead of "succeeding" with whatever Dutch station
happens to be globally nearest - caught live during testing, when a Tokyo/
Dubai fixture in `scripts/test_locations.py` initially resolved to a
real (but ~9000km-away) Dutch station before this cutoff was added.
Resolution only runs once per location and is cached to
`/var/lib/pi-weather-display/rivm_station_cache.json`, re-resolved
whenever the configured `latitude`/`longitude` no longer match the
cache - which happens promptly on a settings-page location change, since
saving new coordinates already forces an immediate re-render
(`web/routes.py:_trigger_rerender`) and that's exactly when the mismatch
gets detected. AQI fetch failures are now fail-soft (log + `None`,
matching `_reverse_geocode`'s existing pattern) rather than aborting the
whole render - previously AQI was bundled into the same Open-Meteo call as
pollen/UV and a bad response there took down the entire render tick.

**Combined scale grows from 4 tiers to 5**, adopting LKI's own bands
(`COMBINED_TIERS = ["Goed", "Matig", "Onvoldoende", "Slecht", "Zeer
slecht"]`) rather than folding LKI down into the old 4-tier scale - doing
that fold would have reintroduced the exact kind of severity-understating
rounding (Open-Meteo's "Redelijk" -> "Goed") that motivated this whole
change. LKI now maps onto `COMBINED_TIERS` 1:1; it's *pollen's* narrower 4
tiers that need a fold now (`POLLEN_TIER_TO_COMBINED = [0, 1, 3, 4]`),
rounding "Hoog" pollen up to "Slecht" rather than down to "Onvoldoende" -
same round-toward-worse principle, just applied to the side that needs it
now. One consequence: pollen alone can never produce "Onvoldoende", only
LKI can - expected, since `max()`-combining doesn't require both inputs to
cover the same range. The AQI gauge (`widgets/gauge.py:render_aqi_gauge`)
gained a 5th arc band reusing black (same precedent the UV icon's
"Extreem" tier already established, `widgets/palette.py`), which in turn
needed a white needle outline (`aqi_needle_outline`, matching the pressure
gauge's existing needle+outline technique) so the needle stays visible
pointing into the new black band instead of vanishing black-on-black -
caught by rendering all 5 gauge states directly during testing.

A fresh-context review (per this repo's Mode 2 rule for multi-file/logic
changes) caught two real gaps before merge, both fixed: `_get_rivm_current_lki`
called `_save_rivm_station_cache` (filesystem I/O) with no try/except,
contradicting the "fails soft throughout" claim - a write failure (e.g. a
read-only SD card) would have aborted the render instead of just skipping
the cache write; and station resolution fetched each candidate's LKI twice
- once to check it publishes LKI at all, then again moments later to read
the actual value - now a single `_rivm_station_lki_value` call serves both,
saving one wasted request per resolution right when ~130 others were just
spent (relevant given the real 300-req/5min limit this session's own
testing tripped more than once).

Deploying to the real Pi (behind the same home IP/NAT as the dev machine
used for the testing above, so sharing luchtmeetnet's rate-limit budget)
surfaced one more real gap: when *every* request in a resolution attempt
gets rate-limited, each one fails as an ordinary non-2xx HTTP response, not
an exception - so the original code's `break`/`continue`-on-bad-status
loops returned `None` completely silently, no log line anywhere, making a
real production rate-limit stretch indistinguishable from "no station
exists" without attaching a debugger. Added explicit warnings at each
early-exit point (station-list fetch failed, per-station geometry lookups
failed, no candidate within range, no in-range candidate returned an LKI
value) - diagnosed the hard way while chasing exactly this symptom on
`pizero`.

**Active** - current design. Verified end-to-end: a real `main.py
--mock-output` render against the configured location resolves and caches
`NL50003` (~5.7km away) and shows "Onvoldoende" (LKI 7 beating grass
pollen's Matig) - a live illustration of the exact discrepancy that
motivated this change; a repeat run reuses the cache with a single request
instead of re-running the ~130-request resolution; changing the location
via the settings web UI (`web_app.py`) correctly re-resolves to a
different, genuinely-nearest station (Amsterdam coordinates -> `NL49019`)
on the very next render, then back to `NL50003` when reverted. Also
confirmed the fail-soft design under real pressure: this session's own
repeated testing tripped luchtmeetnet's 300-req/5min limit more than
once, and each time resolution failed clean (`None`, cache left
untouched, no crash) rather than corrupting state or aborting the render -
not a concern in normal operation, which only ever resolves once per
actual location change. Also verified: the full 13-scenario
`scripts/test_pollen_scenarios.py` suite (rewritten for the 5-tier scale,
two new scenarios covering the Onvoldoende-only-via-LKI and
Hoog-pollen-folds-to-Slecht cases); a full 14-location
`scripts/test_locations.py` regression (no crashes, non-Dutch locations
correctly degrade to "N/A" for the AQI arm - caught and fixed a real bug
along the way, see `RIVM_MAX_STATION_DISTANCE_KM` above); and all 5 gauge
states rendered directly to confirm the new black "Zeer slecht" band and
its needle stay visually distinct.

### 33. Fix UV icon color ignoring the configured saturation
Branch `fix/uv-color-saturation-timing`

`get_uv_color()` read `PALETTE.uv_low/moderate/high/very_high/extreme`,
which are only refreshed by `WeatherCanvas.__init__`'s
`PALETTE.set_saturation(config.inky_saturation)` call - but
`fetch_snapshot()` (which calls `get_uv_color()` via `_parse_data_points`)
always runs *before* `WeatherCanvas` is constructed (`main.py`: fetch at
line 52/67, canvas construction afterward at line 53/73). So the UV icon
was always colored at whatever saturation `PALETTE` last happened to be
synced to - the 0.0 module-load default on every one-shot `main.py` run -
never the render's actually configured `inky_saturation`, for anyone
who's changed that setting from the default. A reintroduction of the
exact bug class entry 26/`docs/plans/palette-saturation-sync-fix.md`
already fixed once, in a different code path.

Found 2026-08-14 while building the (separate, still-unmerged)
forecast-card weather-quality border color feature, which had the
identical pattern - fixed there by threading `config.inky_saturation`
through explicitly instead of reading the timing-dependent `PALETTE`
singleton. Logged to `TODO.md` at the time rather than fixed immediately
(unrelated feature, kept that branch's scope narrow); fixed here as its
own standalone change once asked for.

Same fix applied: `get_uv_color(uv_index, saturation)` and
`_parse_data_points(..., saturation)` now take saturation as an explicit
argument, resolving colors via `native_colors(saturation)` directly
instead of the `PALETTE` singleton's instance attributes -
`fetch_snapshot()` passes `config.inky_saturation` through.

`scripts/test_palette_sync.py` (the file specifically meant to cover
this exact class of bug) gained a new regression test,
`test_get_uv_color_uses_the_saturation_it_is_given` - its three existing
tests only ever checked `PALETTE.saturation` *after* a
`WeatherCanvas`/`render_setup_screen` call, so none of them could have
caught a bug in code (`get_uv_color`, via `fetch_snapshot`) that runs
*before* that sync happens. Worth remembering next time this bug class
shows up somewhere else: check what runs before the palette sync, not
just whether the sync itself works.

**Active** - current design. Verified: `get_uv_color(7, 0.0)` vs.
`get_uv_color(7, 0.7)` now produce different, correctly-computed colors
(previously identical regardless of the second argument); a full
`fetch_snapshot()` → render pass at `inky_saturation=0.7` confirmed the
UV data point's resolved color matches `native_colors(0.7)` exactly; the
full `scripts/test_locations.py` (14 locations), `test_pollen_scenarios.py`,
`test_precip_scenarios.py`, `test_display_freshness.py`, and
`test_palette_sync.py` (including the new test) all pass; and a default
saturation (0.0, unaffected by this fix) live render confirmed
zero visual change for the current production configuration.

A fresh-context review (per this repo's Mode 2 rule) caught two cleanup
gaps the fix itself left behind: `Palette.uv_low/moderate/high/
very_high/extreme` were now dead attributes (nothing reads them since
`get_uv_color` stopped sourcing from the singleton) still sitting under a
comment that claimed otherwise, and `weather_data.py`'s `PALETTE` import
was now unused. Both removed.

### 34. Forecast cards: rain amount next to the icon
Branch `feature/forecast-rain-quality-cards`

The multi-day forecast row now shows the expected rain amount ("3mm",
"0.6mm") next to each day's icon, drawn only when rain is actually
expected. `OPEN_METEO_FORECAST_URL`'s `daily=` list gained
`precipitation_sum` - Open-Meteo's own rain+showers+snowfall
water-equivalent sum, already in mm since `precipitation_unit=mm` was
already fixed for the whole request. `DayForecast` gained
`precip_mm`/`rain_expected`, computed once in `_parse_forecast()` per
this codebase's established separation (classification lives in
`weather_data.py`; widgets only draw what they're handed). See
[settings.md](./settings.md)'s "Forecast cards" section.

**Originally built alongside a second feature - each card's border
colored by overall weather quality** (temperature + precipitation
combined, worst-of-both-wins, the same `max()` idiom entry 32's
"Kwaliteit & Pollen" gauge established), including a mid-build switch
from a filled background to a colored border (sidestepping contrast and
cloud-icon questions a fill would have raised) and two real bugs a
fresh-context review caught before merge (a font-overflow edge case at
high `forecast_days`, and a truncation bug misclassifying some sub-zero
fractional temperatures). **Reverted back to a plain black border at the
user's request** after seeing both live on the real Pi - the colored
version was preserved, un-merged, on `feature/forecast-quality-border-color`
for later; nothing about the rain-mm half needed to change to revert it,
they shared data but not rendering code. That branch's own history
continued separately (entries 39-41): the classification later moved to
an editable `weather_quality.toml`, then was itself merged into `main`
with the border still reverted to black - the classification pipeline is
live in `main` (computed every render) but, same as here, not currently
drawn anywhere.

**A real layout bug caught by rendering, not reasoning about it** (this
part stayed relevant after the revert, since the mm text is still
variable-width): at a higher `forecast_days` setting, cards are narrower
but the icon stays the same height-bound size, so a longer rain amount
like "0.6mm" at a fixed font size overflowed past the card's border -
visible once actually rendered at `forecast_days=10`, not obvious from
the numbers alone. Fixed by giving `widgets/forecast.py` its own
`_fit_font` shrink-to-fit helper, mirroring `WeatherCanvas._fit_font`
(`canvas.py`, entry 22) - can't reuse that one directly (widgets never
import from `canvas.py` - the dependency runs the other way). A
fresh-context review later found this first fix still had an artificial
10px floor on the available width, silently reintroducing the same
overflow at a high enough `forecast_days` (verified at 12, where only 6px
is genuinely available) - removed the floor and instead skip the mm text
entirely when even the smallest font still doesn't fit, same as a dry
day, rather than ever drawing something that overflows.

**Active** - current design. Verified: `scripts/test_forecast_rain_scenarios.py`
(rewritten after the revert to cover just the rain-mm gate - dry, both
sides of the 0.2mm boundary exactly, sub-1mm decimal formatting, a
2-digit whole-mm amount); a full 14-location `scripts/test_locations.py`
regression; and a direct visual check of a real live render confirming
black borders are back and the mm text still renders correctly next to
real rain-cloud icons.

### 35. Icon-Plan.md items 1-3: drop dead `02d`/`02n`, add a hail icon, verify moon-phase offset
Branch `feature/icon-plan-cleanup`

Three of the six items from `Icon-Plan.md` (see that file for the full
proposal and the other three - item 4 accepted as-is/left open, item 5
tracked separately):

- **Item 1**: `02d`/`02n` were generated by `generate_icons.py` and had a
  night-remap entry, but no WMO code actually produced `"02d"` -
  codes 1/2 map straight to the `022d`/`022n` composite instead. Removed
  the two `_icon_map()` entries, the night-remap dict entry, the two PNG
  assets, and their `docs/icons.md`/`docs/attribution.md` references.
  Zero behavior change - pure dead-code removal.
- **Item 2**: thunderstorm-with-hail (WMO 96/99) previously shared plain
  `11d` with ordinary thunderstorm (95) for every icon call site (only the
  chart's precipitation axis label distinguished hail, per entry 20). Added
  a new `96d` icon key (`wi-day-hail`, reusing the `storm` palette color,
  no night variant - matching `11d`, which also has none), split
  `map_weather_code_to_icon`'s combined `[95, 96, 99]` case into `[95]` ->
  `11d` and `[96, 99]` -> `96d`.
- **Item 3**: verified the forecast-card moon-phase `target_date = dt.date()
  + timedelta(days=1)` offset against publicly published reference dates
  (2026-09-10 new moon, 2026-09-26 full moon) via a throwaway script calling
  `astral.moon.phase()` directly - the `+1` target date matched within
  0.34/0.04 days vs. 2.20/0.97 days unshifted, confirming the existing
  offset is correct. No functional change; added a confirming code comment
  at the `target_date` line and updated `docs/icons.md`'s note from
  "worth double-checking" to verified.

**Active** - current design. Verified: regenerated the full icon set
(`scripts/generate_icons.py`, using a fresh local `erikflowers/weather-icons`
clone) and confirmed every icon other than the `02d`/`02n` removal and `96d`
addition rendered byte-identical; visually inspected the regenerated
`docs/images/icon_overview.png` gallery; the full `scripts/test_locations.py`
(14 locations, 3 modes) regression passed.

### 36. Icon-Plan.md item 5: bake extra thickening into `01n`
Branch `feature/icon-plan-01n-thicken`

`01n` (`wi-night-clear`) read noticeably thinner than the `wi-moon-*`
phase icons it sits next to at the same render size, despite sharing
`PALETTE.moon` - a source-SVG stroke-weight mismatch. Added
`EXTRA_THICKEN = {"01n": 1.0}` to `generate_icons.py`'s main icon loop
(the only icon special-cased outside `COMPOSITE_ICONS`): loads via the
existing `_render_svg()` helper, applies `thicken_icon(..., strength=1.0)`,
saves - every other icon still takes the original raw-`resvg_py.svg_to_bytes`
fast path unchanged.

The plan's own `0.75` "middle-ground" starting guess turned out wrong.
A pixel-level check - the fraction of `01n`'s alpha-channel pixels that
are semi-transparent ("ambiguous", the ones dithering actually struggles
with) rather than either fully opaque or fully transparent - at strengths
`[0.0, 0.25, 0.5, 0.75, 1.0]` measured `[0.117, 0.228, 0.232, 0.229,
0.101]`. Every *partial* strength roughly doubles the ambiguous-edge
fraction relative to either endpoint: `thicken_icon`'s `MaxFilter` blend
(`strength` interpolates between the original and a full 1px dilation)
bakes in its own soft edge on top of the SVG's original antialiasing,
rather than avoiding it. Only a full 1px dilation (`strength=1.0`) is
simultaneously bolder and cleaner - which is exactly why the `022d`/`022n`
composite's back layer already uses `1.0` rather than a partial value
(entry 13), not a coincidence worth re-guessing past.

**Scope correction, caught by fresh-context review**: an initial pass at
this fix claimed it made `01n` "hold up fine" next to the `wi-moon-*`
phase icons. That overclaimed what thickening alone can do. A
matched-size, matched-treatment side-by-side (both `01n` and each phase
icon run through their own real `thicken_icon()` call, `AssetStore`-loaded
at 30px) showed `01n` reading as a visibly chunkier, denser ring shape
next to the phase icons' cleaner, mostly-solid crescent/disc silhouettes.
Root cause: `wi-night-clear` is a **hollow ring outline**, a fundamentally
different SVG topology from most `wi-moon-*` icons, which are
**solid-filled** shapes - no stroke-weight adjustment closes a topology
gap. Tried `_solid_fill()` (already used on the `022d`/`022n` composite's
cloud layer) as a fix for *that*: filling `01n`'s hollow ring solid
produces a near-full disc with a small notch, not a crescent - moves
further from the phase family's look, not closer. Rejected.

**Active** - current design, scope narrowed to match what was actually
verified: this fixes the literal complaint ("`01n` reads thin/pale, an
antialiased-edge-heavy outline that dithers poorly"), not a full
silhouette match to the `wi-moon-*` family (a harder problem needing a
different source SVG or a custom glyph - left open). Verified: regeneration
touched only `assets/icons/01n.png` (confirmed via `git status`); visually
compared `docs/images/icon_overview.png` and an `AssetStore`-pipeline
side-by-side against `newmoon`/`waningcrescent`/`firstquarter`/`fullmoon`
(first at mismatched treatment, which is what caught the overclaim above,
then matched); confirmed `01n` still reads as a legible, bold crescent in
isolation at both the 102px current-conditions size (no runtime thickening
there) and the 30px chart-strip size (runtime thickening stacks on top) -
improved over the pre-fix thin/pale version, not silhouette-matched to its
siblings; full `scripts/test_locations.py` (14 locations, 3 modes)
regression passed.

### 37. Forecast cards: mm unit moved below the rain number
Branch `feature/forecast-mm-unit-below-number`

The rain-mm text next to each forecast card's icon was a single inline
string ("0.6mm", "20mm"). Split into two stacked lines - the number on
top, "mm" below it - so the number reads first at a glance. No
`weather_data.py`/`DayForecast` change - `precip_mm`/`rain_expected` were
already separate fields, this only changed how `widgets/forecast.py`
draws them.

A first pass added a *separate* vertical-fit check alongside the existing
horizontal one (two stacked lines need roughly twice the vertical room the
old single line did) - a numeric sweep across `forecast_days` 8-30 showed
the horizontal check already happens to gate this in practice (the same
shrinking `icon_size` that tightens vertical headroom also tightens
horizontal room), but checking it sequentially rather than jointly meant a
smaller font size that could satisfy *both* constraints would never be
tried once a larger size already passed the width-only check, per a
fresh-context review. Replaced `_fit_font` with `_fit_stacked_lines`
(`widgets/forecast.py`): one shrink-to-fit loop that checks width and
height together per candidate size and returns the draw position
directly, rather than two sequential checks with the position math
duplicated between the fit check and the actual draw call. `_fit_font`
itself was then dead code (no other caller in this file) and removed. A
second review pass caught one more small duplication - `_fit_stacked_lines`
now returns the already-measured block width alongside the font/position
tuple, instead of the caller re-measuring both strings a second time.

Also found, logged to `TODO.md`, and deliberately **not** fixed here
(pre-existing, unrelated): with `show_moon_phase=True` and a wide rain
amount, the moon-phase percentage row can visually overlap the day-name/
temps text above it - reproduced against the pre-this-change code too
(`git stash`), so out of scope for this change's diff.

**Active** - current design. Verified: `scripts/test_forecast_rain_scenarios.py`
(unaffected - it asserts `DayForecast` fields, not pixel layout); visually
inspected every scenario's rendered card (sub-1mm decimal, 2-digit whole-mm,
dry) after each revision of the fit logic; confirmed via a data-level check
(not just the render) that a synthetic 12-card/2-digit-mm scenario has
`rain_expected=True` on every card yet correctly omits the text
(tightest-width case, matching how the original mm-text overflow bug -
entry 34 - was found); a 30-card extreme case (`forecast_days=30`,
unbounded by `settings_store` validation) confirmed no text is drawn there
either, with no vertical collision; confirmed no collision with the
moon-phase row in the normal (non-overlapping-bug) case
(`show_moon_phase=True`); full `scripts/test_locations.py` (14 locations,
3 modes) regression passed after every revision.

### 38. Forecast cards: mm-rain text matches the day-code/temps size and weight
Branch `feature/forecast-mm-unit-below-number`

The rain-mm number/unit (entry 37) was drawn `normal`-weight, capped at
12px regardless of card width - noticeably smaller and lighter than the
bold day-name/high-low-temp text right below it in the same card, at the
user's request to match. `draw_forecast_card` (`widgets/forecast.py`) now
computes `bold_size = max(10, int(region.w * 0.15))` once and passes it
as both the mm-text's ideal max size and the day-label/temps font's size,
so the two can't drift apart by editing one and not the other; the
day-name/code itself (`day.day_label`) already shared the bold size/weight
with the temps text before this change - only the mm-rain text's style
changed. `_fit_stacked_lines` always draws bold now (its one caller's only
use).

**A multi-agent fresh-context review (7 parallel finder passes) caught two
real bugs in the first version of this change**, both independently
confirmed by more than one agent and reproduced directly:

1. **Parity bug silently dropping valid text.** The shrink loop stepped
   by 2px (`range(max_size, min_size - 1, -2)`), which only ever reaches
   `min_size` (8) when `max_size` shares its parity. The old code always
   passed a fixed even `max_size=12`, so this never mattered; `bold_size`
   varies continuously with card width and lands on odd values roughly
   half the time. Reproduced concretely: `forecast_days=11`, a day
   forecasting 20mm - size 8 genuinely satisfies both width and height,
   but the old loop (starting from odd `bold_size=10`... `9` in some
   width buckets) never tried it, so the text silently vanished (icon
   just re-centered as if dry) even though a valid rendering existed.
   Fixed by stepping 1px at a time instead of 2px - `min_size` is now
   always reached.
2. **"Can't drift apart" was an overclaim.** `bold_size` is sized off the
   full card width, but the mm-text only has `region.w` minus the icon
   and gaps to work with, and its vertical budget is pinned to
   `icon_size` (capped independently of card width once cards get wide
   enough) rather than to `bold_size` itself - so at `forecast_days`
   below the default (7), the mm-text provably shrinks below `bold_size`
   even though plenty of horizontal room exists. Not fixed (would mean
   reworking the card's vertical budget - out of scope for a font-size
   match); logged the gap plus a related, pre-existing, unrelated bug
   found along the way (`font_bold` itself has no shrink-to-fit and
   overflows badly at very low `forecast_days`) to `TODO.md`.

A third, lower-severity finding from the same pass (the block's height
check allowed it to land literally flush against the day-label row, no
clearance) is also fixed - `_fit_stacked_lines` gained a `margin`
parameter (default `1`px, deliberately small: the natural gap at the
default `forecast_days=7` is itself only ~1px, so a bigger default margin
would shrink the mm-text below the day-label/temps size at the *default*
setting, undermining the whole point of sharing that size).

**A follow-up review pass caught two more issues in that fix**, one a
second overclaim, one an efficiency regression:

3. **The "matches at forecast_days=7 and higher" correction (above) was
   itself still wrong.** A full sweep (`forecast_days` 1-17) showed the
   match band is actually 7 *through 10*, not open-ended upward - above
   10, `available_width` becomes the binding constraint (same as before
   this change existed) and the text shrinks or omits itself the same way
   it always has. Corrected `docs/settings.md` to state the real,
   verified band instead of guessing past what was actually measured.
4. **Unbounded loop start caused wasted work at low `forecast_days`.**
   The shrink loop started at `bold_size` directly, and `bold_size` has
   no upper bound (`settings_store` only validates `forecast_days > 0`,
   so `forecast_days=1` yields `bold_size≈120`) - but the height
   constraint can never actually pass above a modest ceiling regardless
   (derived from `icon_size`'s own fixed cap). Every rainy card at a low
   `forecast_days` was iterating and font-shaping (`getlength()`, not
   cached, unlike the font object itself) dozens of pointless sizes on
   every render - a real Pi Zero W cost. Capped the loop's start (`32`,
   with real headroom above the observed ceiling - see point 5) and
   reordered the checks so the cheap, text-independent height check runs
   *before* the two `getlength()` shaping calls, skipping them entirely
   for a size the height check would reject anyway - verified zero
   change in the actual chosen font size across the full `forecast_days`
   1-17 sweep, a pure efficiency fix.

**A second follow-up pass (8 parallel finders) caught one more real bug -
the height check's own formula didn't match what actually gets
rendered:**

5. **Height check was off by half a line-height, needlessly shrinking
   text.** Both lines are drawn with `anchor="lm"` (each line's y is its
   own vertical *center*), so the block's true bottom edge is
   `top_line_y + 1.5 * line_h` - but the check computed
   `top_line_y + 2 * line_h`, a full half-line more conservative than
   the real geometry. Confirmed both algebraically and empirically
   (`forecast_days=6`: old formula capped at font size 15, a
   geometrically-correct formula reaches 18 - `bold_size` exactly).
   Fixed the formula to match the actual rendered bottom edge, which
   widened the real exact-match band from `forecast_days` 7-10 to
   **5-10** - not a new feature, a correctness fix that happened to
   recover headroom the layout already had. This also raised the
   observed height ceiling from ~15px to ~23px, which is why point 4's
   loop-start cap moved from `24` to `32` (barely any headroom would
   have been left otherwise).

**Active** - current design. Verified: visually inspected every rain
scenario (sub-1mm decimal, 2-digit whole-mm) at the default width and at
`forecast_days=6` specifically (the band-widening fix's clearest case -
"0.6"/"mm" visibly larger, matching the day-label size); directly
reproduced the parity bug's exact failure scenario (`forecast_days=11`,
20mm) against the pre-fix code and confirmed the post-fix code renders
"20"/"mm" instead of nothing; measured the actual pixel gap between the
mm-block and the day-label row at the default `forecast_days=7` (1px
before the margin fix) to size the `margin` parameter correctly rather
than guessing; a full `forecast_days` 1-17 sweep (both a decimal and a
2-digit amount) confirmed the exact-match band, first found to be 7-10,
is really 5-10 after the height-formula fix, and that graceful
shrink/omission above and below that band still works the same as before
this change; confirmed the loop-start cap and check-reordering produce
byte-identical chosen font sizes across that entire sweep - efficiency-only,
no behavior change; confirmed `show_moon_phase=True` shows no *new*
interaction beyond the pre-existing, already-logged moon-row overlap
(`TODO.md`); full `scripts/test_forecast_rain_scenarios.py` and
`scripts/test_locations.py` (14 locations, 3 modes) regressions passed
after every revision.

### 39. Forecast cards: rain amount + weather-quality border color (original build)
Branch `feature/forecast-rain-quality-cards`

Two additions to the multi-day forecast row, requested together since
both need the same new daily-precipitation data: (1) the expected rain
amount ("3mm", "0.6mm") drawn next to each day's icon, only when rain is
actually expected; (2) each card's border colored by how pleasant that
day's weather is overall (temperature + precipitation combined), using
the same worst-of-both-wins `max()` idiom entry 32's "Kwaliteit & Pollen"
gauge already established.

`OPEN_METEO_FORECAST_URL`'s `daily=` list gained `precipitation_sum` -
Open-Meteo's own rain+showers+snowfall water-equivalent sum, already in
mm since `precipitation_unit=mm` was already fixed for the whole request.
`DayForecast` gained `precip_mm`/`rain_expected`/`quality_tier_index`,
all computed once in `_parse_forecast()` per this codebase's established
separation (classification lives in `weather_data.py`; widgets only draw
what they're handed). A fresh small `FORECAST_QUALITY_TIERS` scale
(`["Goed", "Matig", "Slecht", "Zeer slecht"]`) - deliberately not
`COMBINED_TIERS`, which is entry 32's own 5-tier AQI/pollen scale, a
different concern.

**Changed mid-build from a filled card background to a colored border**
(confirmed with the user) - simpler, and it sidesteps two questions a
filled background would have raised: text/icon contrast against a
saturated fill, and a hardcoded-white "cloud interior" icon element
(`widgets/palette.py`'s `cloud_interior`, baked into the icon PNGs at
generation time) no longer reading as "paper showing through" against a
non-white card. With the border-only approach neither applies - the card
interior stays exactly as it always was.

**A real layout bug caught by rendering, not reasoning about it**: at a
higher `forecast_days` setting, cards are narrower but the icon stays the
same height-bound size, so a longer rain amount like "0.6mm" at a fixed
font size overflowed past the card's border - visible once actually
rendered at `forecast_days=10`, not obvious from the numbers alone. Fixed
by giving `widgets/forecast.py` its own `_fit_font` shrink-to-fit helper,
mirroring `WeatherCanvas._fit_font` (`canvas.py`, entry 22) - can't reuse
that one directly (widgets never import from `canvas.py` - the dependency
runs the other way), so this is a small intentional duplication of the
same two-line pattern rather than a cross-module refactor for it.

**A fresh-context review (per this repo's Mode 2 rule) caught two more
gaps before merge, both fixed**: (1) the first `_fit_font` fix still had
an artificial 10px floor on the available width, so it silently
reintroduced the same overflow at a high enough `forecast_days` (verified
at 12, where only 6px is genuinely available) - removed the floor and
instead skip the mm text entirely when even the smallest font still
doesn't fit, same as a dry day, rather than ever drawing something that
overflows; (2) `_temp_quality_tier` was fed the already-int-truncated
`high` used for display, and `int()` truncates toward zero, so a real
high of e.g. -0.3°C became `0` and landed a tier too nice ("Matig"
instead of "Slecht") - fixed by classifying off the raw float before
truncation, leaving the display value untouched.

**Outdated - superseded by entry 41** (reverted to a plain black border,
the classification pipeline preserved but unused). Verified at the time:
`scripts/test_forecast_quality_scenarios.py` (new, 12 scenarios - every
tier, both boundary edges exactly at 0.2mm/26°C, the two inputs
disagreeing in opposite directions, the mm-text on/off gate); a full
14-location `scripts/test_locations.py` regression (no crashes, run
twice - before and after the review fixes); direct visual checks of a
real live render (a 36°C day correctly red, rainy days correctly
yellow/orange with sensible mm amounts next to real rain-cloud icons),
the `forecast_days=10` + `show_moon_phase=True` tight-layout case that
caught the first overflow bug, and `forecast_days=12` (the review's own
flagged case) confirming the text now omits cleanly instead of
overflowing; and the exact boundary values (-0.3°C, -5.7°C) the review
traced through `_temp_quality_tier` by hand to confirm the truncation fix.

### 40. Forecast-card quality tiers move to an editable weather_quality.toml
Branch `feature/forecast-quality-border-color`

Entry 39's temperature/precipitation ranges and colors were hardcoded
Python (`_temp_quality_tier`/`_precip_quality_tier`/
`FORECAST_QUALITY_TIERS`). The user wants to edit the scheme themselves
without touching code - confirmed keeping today's exact values for now
("keep the existing color system, I will edit later"), so this is purely
a mechanism change, not a redesign. New `weather_quality.toml` (repo
root) holds an ordered `[tiers]` table (name -> color, declaration order
*is* severity order) plus two ordered `{max, tier}` band lists for
temperature and precipitation - an exact re-encoding of the previous
hardcoded bands. TOML over YAML/JSON: Python's stdlib `tomllib` (shipped
since 3.11, confirmed available - the deployed Pi runs 3.13.5) needs no
new dependency, and unlike JSON it supports comments, which matters since
the file's whole purpose is being hand-edited later without reading
`weather_data.py` to understand it.

`weather_data._load_weather_quality_config()` re-reads the file fresh on
every render tick (no caching - `main.py` is already a one-shot process
per tick, matching `config.py`/`settings_store.py`'s own re-read-every-run
pattern) - an edit takes effect on the very next scheduled render, no
restart needed. **Fails soft** on any problem (missing file, unparseable
TOML, a tier/color reference that doesn't resolve) by falling back to a
hardcoded copy of the shipped defaults, logging a warning rather than
crashing the render - the same leniency `settings_store.load_config()`
already applies to a corrupted `settings.json`, needed here for exactly
the same reason: a hand-edited file is exactly what typos happen to.

`DayForecast.quality_tier_index` (an int into `FORECAST_QUALITY_TIERS`)
became `quality_border_color` (the resolved RGB tuple) -
`weather_data._quality_tier_and_color()` now does the full temperature/
precipitation-tier lookup *and* the tier-name-to-color resolution in one
place, so `widgets/forecast.py` just uses the value directly as the
border's `outline=` color with no lookup of its own. This also let
`widgets/palette.py`'s `forecast_border_good/fair/poor/bad` fields and
the `PALETTE` import in `widgets/forecast.py` go away entirely -
`native_colors()` (already used for exactly this name-to-RGB resolution
elsewhere) is now called from `weather_data.py` directly instead of
being wrapped in dedicated `Palette` fields, and nothing else needed
them. `rain_expected` now derives from the same config's precipitation
table instead of a separate `FORECAST_DRY_MM_THRESHOLD` constant, so the
border color and the mm-text gate can't drift out of sync from two
separately-hand-edited numbers.

**A fresh-context review (per this repo's Mode 2 rule) caught four real
gaps before merge, all fixed**: (1) the border color was resolved via the
shared `PALETTE.saturation`, but `fetch_snapshot()` (which computes it)
always runs *before* `WeatherCanvas.__init__` ever calls
`PALETTE.set_saturation(config.inky_saturation)` for that render - so
anyone with a non-default `inky_saturation` got the 0.0 module-load
default's colors instead, a reintroduction of the exact bug class entry
26 already fixed once. Fixed by threading `config.inky_saturation`
through `_parse_forecast`/`_quality_tier_and_color` explicitly instead of
reading the timing-dependent singleton - confirmed the same bug still
exists, unfixed, for `get_uv_color()` (pre-existing, unrelated to this
branch), logged to `TODO.md` rather than fixed here. (2)
`_validate_weather_quality_config` didn't require the last
temperature/precipitation band to be a catch-all (no `max`) - a config
missing one would silently score an out-of-range extreme value (e.g. a
45°C day) as the *best* tier instead of the worst, via `_band_tier`'s
defensive fallback. (3) it also didn't check that a band's `max` was
actually numeric - a quoted value (`max = "cold"`) passed validation and
then crashed `_band_tier`'s `<` comparison, contradicting the whole
fail-soft premise. (4) `_load_weather_quality_config`'s exception handler
didn't catch `UnicodeDecodeError`, so a non-UTF-8 hand-edit (a realistic
mishap for a file explicitly meant to be edited by hand) crashed the
render instead of falling back.

**Active** - current design. Verified: zero behavior change confirmed by
diffing a live render taken immediately before and after switching to
the file-driven path (identical colors, same location/day); an
edit-takes-effect check (changed `Matig`'s color to blue in the TOML
file, re-rendered with no code change, confirmed blue appeared, then
reverted); `scripts/test_forecast_quality_scenarios.py` (rewritten to
assert resolved RGB colors instead of tier indices, plus 6 fail-soft
scenarios - missing file, invalid color, unparseable TOML, non-UTF-8
bytes, a missing catch-all band, and a non-numeric `max` - and a
dedicated saturation-threading scenario reproducing finding (1) against
a non-default `inky_saturation`); and a full 14-location
`scripts/test_locations.py` regression, run both before and after the
review fixes.

### 41. Forecast cards: revert to a plain black border, keep the weather-quality pipeline
Branch `feature/forecast-quality-border-color`

Entries 33-34's colored border (temperature+precipitation tier ->
resolved color, drawn as the card's `outline=`) is reverted back to a
plain black border (`PALETTE.card_border`) - at the user's explicit
request, so they can reuse the classification for a different visual
treatment later ("I will use them later") rather than losing the work.
Only `widgets/forecast.py`'s `draw_forecast_card` changed (one line:
`outline=day.quality_border_color` -> `outline=PALETTE.card_border`,
`width=3` -> `2` to match this repo's other black-border precedent) -
`weather_data.py`'s entire weather-quality pipeline (`weather_quality.toml`,
`_load_weather_quality_config`, `_validate_weather_quality_config`,
`_band_tier`, `_quality_tier_and_color`, `DayForecast.quality_border_color`)
is untouched and still computed every render, just not consumed for the
border anymore. `widgets/palette.py`'s `card_border` field (already
present, previously unused by forecast cards specifically) is back in
active use; its comment updated to say so instead of claiming no one
reads it.

**Active** - current design. Verified: `scripts/test_forecast_quality_scenarios.py`
still passes unchanged (asserts `DayForecast.quality_border_color`
directly - a data-level check, unaffected by what the widget draws with
it); visually confirmed a scenario expected to resolve red (heavy rain,
mild temp) now renders with a plain black border instead; full
`scripts/test_locations.py` (14 locations, 3 modes) regression passed.

### 42. Chart: whole-number rain axis, bigger axis-number font
Branch `feature/chart-axis-polish`

`widgets/chart.py`'s rain-axis max (`rain_axis_max`) rounded up to the
nearest tenth, so its top label could show a decimal (e.g. "4.5"); now
rounds up to the nearest whole number instead, so the label is always an
integer. This made `_decimal_point_center_x()` and its decimal-alignment
branch for the rotated precip label (`"Regen [mm]"` etc.) permanently
dead code - removed, the precip label now always uses its flat 10px gap
off the axis line.

Separately, the left (temperature) and right (rain) axis-extreme number
labels (`max_temp`/`min_temp`/`rain_axis_max`/`0`) now draw in a new,
larger `font_axis` param (18px bold, up from the shared 14px `font_bold`)
passed into `render_chart()` from `canvas.py`. `LEFT_MARGIN` widened
46px -> 58px to fit the larger temperature labels (measured worst case
`"-36°C"` at 18px = 48px +6px gap); `RIGHT_MARGIN` (42px) needed no
change - worst-case 3-digit rain label at 18px (32px +6px gap) still
fits under it.

Initially only the axis-extreme labels moved to `font_axis`, leaving the
chart's other horizontal-line temperature labels (the `show_temp_gridlines`
mode's "10°"/"20°"/etc. gridline tick labels, the non-gridlines mode's
dashed actual-min/max labels, and its dashed 0° reference-line label) on
the smaller `font_bold` - but the user pointed out the gridline tick
labels still read small next to the now-bigger axis numbers, so all three
moved to `font_axis` too for a consistent size across every temperature
label on the chart. Only the rotated precip label (`"Regen [mm]"` etc.)
and the x-axis hour labels stayed on their original fonts.

Two collision-avoidance spots needed re-tuning for the new font size: in
`show_temp_gridlines` mode, the gap that suppresses a gridline's own tick
label when it's too close to the axis-extreme label (`min_label_gap`, and
the unit-suffix-width shift that keeps the gridline labels' numbers
column-aligned with the axis-extreme labels) was still measured off
`font_bold` - a subagent review (see Mode 2's diff-review step) caught the
`min_label_gap` half before it shipped; both now measure off `font_axis`,
matching the font the labels actually draw in.

**Active** - current design. Verified: `scripts/test_locations.py` (14
locations, 3 modes) and `scripts/test_precip_scenarios.py` (rain/hail/
snow/dry) both pass; visually confirmed no decimal point on the rain
axis, every temperature label on the chart (axis extremes, gridline
ticks, dashed min/max, zero-line) at the same larger size, no clipping at
either margin, and (in gridlines mode) a genuine near-miss case - Dubai's
max_temp=43 vs. a would-be "40°" gridline tick, only 3° apart - still
correctly suppresses the tick label instead of overlapping it.

### 43. Rain axis: intensity-category labels instead of mm numbers
Branch `feature/rain-axis-intensity-labels`

The right (rain) axis's two numbers (a rounded-up mm ceiling at top, "0"
at bottom) are replaced with Dutch rain-intensity category words for
rain/hail windows (`"Regen [mm]"`/`"Hagel [mm]"` - both plot the same
mm/h `precipitation` series): `droog` (<0.01mm/h), `motrgn` (0.01-1.0),
`licht` (1.0-2.5), `matig` (2.5-10), `zwaar` (10-50), `hevig` (50+) -
`widgets/chart.py`'s new `RAIN_INTENSITY_BANDS`/`_rain_intensity_label()`.
Snow (`"Sneeuw [cm]"`, a different unit) and dry (`"Droog"`) windows keep
the old plain numeric axis unchanged.

Showing all 6 bands as an always-on ladder was ruled out up front -
measured word widths ("Moderate", before shortening to Dutch) exceeded
the entire ~42px right margin on their own, and the ~104px-tall plot area
has no room for 6 stacked rows at any legible size. Settled on the same
idiom the temp axis already uses for its actual min/max (entry 15): only
label *today's actual range* - the axis's existing top/bottom positions
now show whichever band the window's real max/min hourly value falls
into (not the rounded-up `rain_axis_max` ceiling used for the bars'
unchanged linear scale), so a day that's mostly dry with a few rainy
hours shows e.g. "licht" at top and "droog" at bottom. `RIGHT_MARGIN`
widened 42px -> 82px to fit the longest label ("motrgn") - a subagent
review caught that the first pass (70px) was sized only against the
`jost` font, measuring 60px there, but `config.py`'s actual default
`font_family` is `bitter` (`"jost"` is the non-default alternative), where
the same word measures 71px - would have clipped off the 800px canvas
edge under the app's own default settings. Re-measured against both
font families and re-verified with a scratch fixture rendered under the
default `bitter` config before shipping.

Two rounds of clarifying questions (AskUserQuestion) shaped this before
implementation: layout approach (today's-range-only vs. all 6 abbreviated
vs. growing the chart taller), precip-type scope (rain-only vs. rain+hail
- hail was included, snow/dry excluded), and label language (initially
given in English, moved to Dutch to match every other chart/screen label
- with two more user-requested tweaks: `geen`->`droog`, `motregen`->
`motrgn` for width).

**Active**, except that this behavior was unconditional (always-on for
rain/hail) at the time it was written - **entry 44** makes it an opt-in
`rain_axis_format="category"` setting, defaulting to the original plain-
mm axis. The bands/labels/logic described here are otherwise unchanged.
Verified: `scripts/test_locations.py` and `scripts/test_precip_scenarios.py`
both pass unchanged - the existing "rain" fixture (constant 2.4mm/h)
incidentally covers the same-band top/bottom case ("licht"/"licht"),
"hail" (1.0-3.5mm/h) covers two different bands ("matig"/"licht"),
"snow"/"dry" confirm those stay numeric; a one-off scratch fixture
(60mm/h peak, ~0mm/h trough) confirmed the "hevig"/"droog" extremes also
render without clipping.

### 44. Rain axis format as a setting: mm vs category labels
Branch `feature/rain-axis-intensity-labels`

Entry 43's intensity-word rain axis was shipped unconditional; this adds
a `DisplayConfig.rain_axis_format` setting (`"mm"` \| `"category"`,
default `"mm"` - preserves the original plain-numeric axis for anyone not
opting in) following the exact generic pattern every other 2-choice
string setting already uses (`font_family`/`time_format`): one validator
in `settings_store.py`'s `FIELD_VALIDATORS`, one `_set(...)` line in
`web/routes.py`'s form parser, one `<select>` in `settings.html`'s
"Weergave" fieldset - no new mechanism needed anywhere. `render_chart()`
gains a `rain_axis_format` parameter threaded from `canvas.py`, and its
existing `if precip_label in INTENSITY_LABELED_PRECIP:` check
(unconditional in entry 43) gains a `rain_axis_format == "category"`
guard.

Also addressed: in category mode, the rotated side label drops its now-
inaccurate `"[mm]"` unit suffix (`"Regen [mm]"` -> `"Regen"`,
`"Hagel [mm]"` -> `"Hagel"`, via `str.removesuffix`) - snow/dry labels
are untouched either way, since they're never in intensity-label mode.

**Active** - current design. Verified: `scripts/test_locations.py` and
`scripts/test_precip_scenarios.py` pass with the new `"mm"` default,
confirming it reproduces the pre-entry-43 plain-numeric axis; a scratch
fixture rendered both `rain_axis_format` values side by side, confirming
`"category"` still works correctly as an opt-in and the `"[mm]"` suffix
drop applies only there; manually exercised `web_app.py`'s `/settings`
page locally (`curl` POST round-trip) to confirm the new dropdown saves
and persists. Fresh-context subagent review found no issues.

### 45. Shared temp/rain gridlines in "gridlines"/"compact" mode
Branch `feature/shared-temp-rain-gridlines`

`show_temp_gridlines` mode's every-10° reference lines now also label
the rain value at that same height, for rain/hail windows only
(`show_rain_gridline_labels`) - `y_temp()` and `y_rain()` already map
their two different scales onto the exact identical `plot_y0..plot_y1`
pixel range (`y_temp(max_temp)`/`y_rain(rain_axis_max)` both exactly
`plot_y0`, `y_temp(min_temp)`/`y_rain(0)` both exactly `plot_y1`), so
every gridline's height already corresponds to a specific rain value -
this labels it instead of drawing a second independent rain grid, per
the user's explicit ask ("can we have shared lines so for instance 10
degrees is same line as moderate rain?"), addressing the plot's limited
~104px height without doubling the line count. `_format_rain_number()`
added to keep the gridline and axis-extreme numeric labels formatted
consistently (one decimal, shared helper).

Two real bugs surfaced only through rendering and review, not from the
plan itself:
- The rotated `"Regen [mm]"`/category-word side label occupies ~90px of
  the ~104px plot height, centered - almost any gridline label landed
  directly on it, confirmed illegible in rendered screenshots. Resolved
  (user's choice, offered as one of three options) by dropping the side
  label whenever a gridline label actually gets drawn
  (`any_gridline_labeled`) - not unconditionally on `show_temp_gridlines`,
  since a narrow-enough temp range can suppress every gridline via the
  existing extreme-collision check, in which case the side label still
  shows (nothing else identifies the axis as rain otherwise).
- A subagent review then caught that snow/dry windows were also getting
  bare, unit-less gridline numbers (e.g. "0.5" with no "cm"/"Droog"
  context) once the side-label suppression applied broadly - scoped the
  entire gridline-rain-label feature (drawing it and suppressing the side
  label) to `show_rain_gridline_labels = precip_label in
  INTENSITY_LABELED_PRECIP` (rain/hail only); snow/dry keep the chart's
  original gridline-mode behavior untouched.
- A second subagent-review round flagged inconsistent numeric rounding
  between the new gridline labels and the existing axis-extreme label
  (fixed via `_format_rain_number`), a redundant per-iteration
  `getbbox()` call (hoisted above the loop), and duplicated comments
  (trimmed).

`scripts/test_precip_scenarios.py` extended to also render the "rain"/
"hail" scenarios under `rain_axis_format="category"` in every screen
mode (`*_category.png`) - closes a real coverage gap a subagent review
found (gridlines/compact x category was previously untested).

**Active** - current design. Verified: `scripts/test_locations.py` and
the extended `scripts/test_precip_scenarios.py` pass; visually confirmed
across live rain (Mumbai), dry (Dubai), and crafted rain/hail/snow/dry
fixtures that gridline rain labels render without collision, snow/dry
correctly keep their side label and skip bare numbers, and a scratch
fixture with an artificially narrow temp range confirmed the side label
correctly reappears when every gridline gets suppressed. Two rounds of
fresh-context subagent review both surfaced real, fixed issues before
this shipped.

---

### 46. Gridline labels win axis-extreme collisions; bigger current-conditions text
Branch `feature/chart-label-swap-current-conditions-font`

Two small polish fixes:

- In `show_temp_gridlines` mode ("gridlines"/"compact"), when a 10°
  gridline lands close enough to the chart's max/min-temp axis-extreme
  label to collide with it, entry 45's code suppressed the *gridline's*
  label and kept the axis-extreme one. Per explicit user ask ("When the
  max temp and the highest dotted line temp label overlap, remove the
  max temp label instead of the dotted line label"), this is now
  flipped: the axis-extreme label (`suppress_max_temp_label`/
  `suppress_min_temp_label`) is skipped and the gridline's own label -
  which, on rain/hail windows, also carries the shared rain reading -
  always draws instead. Extended the same swap to the rain-axis top/
  bottom extreme labels (`suppress_max_rain_label`/
  `suppress_min_rain_label`) for the same collision risk on the right
  side.
- A fresh-context subagent review caught a real bug in that rain-side
  extension: it originally reused the temp-side proximity check
  (`near_max`/`near_min`, measured against `max_temp_y`/`min_temp_y`),
  which silently breaks on a degenerate all-hours-exactly-0°C window -
  `temp_span`'s `or 1` fallback decouples `min_temp_y` from its normal
  `plot_y1` position, and the wrongly-derived signal could suppress a
  rain-axis label that wasn't actually colliding with anything,
  disappearing off the chart. Fixed by checking rain-side proximity
  against `plot_y0`/`plot_y1` directly (always the true rain-axis
  extremes by construction) instead of the temp-derived `max_temp_y`/
  `min_temp_y` - identical behavior in every normal (non-degenerate)
  case, correct in the edge case too. Verified via a crafted 24-hour
  all-0°C-with-rain fixture, both before and after the fix.
- `canvas.py`'s current-conditions panel (top-left "Gevoelstemp. X°" and
  "min / day-high / min" lines) bumped from bold-15 to bold-19, with
  their vertical offsets adjusted (`temp_y + 40`/`temp_y + 74`, was
  `+34`/`+56`) to reclaim unused whitespace between that panel and the
  chart below - `CHART_AREA`'s position in `layout.py` is untouched, so
  the chart itself doesn't shift. Verified no overflow/overlap via both
  real renders and direct `textbbox` measurements against the widest
  realistic case (double-digit negative temps, both font families).
- On dry ("Droog") windows, the rain axis's top extreme label used to
  always show `rain_axis_max` - but that value is always the
  `max(1, ...)` placeholder floor on a dry day (there's no real rain to
  size the axis off), so the "1" it showed implied a reading that never
  happened. Dropped for `precip_label == "Droog"` specifically, per
  explicit user ask - the bottom "0" and the "Droog" side label are
  unaffected, and rain/hail/snow windows are untouched (their top label
  reflects real data).

**Active** - current design. Verified: `scripts/test_locations.py`,
`scripts/test_precip_scenarios.py`, `scripts/test_pollen_scenarios.py`,
`scripts/test_display_freshness.py`, and `scripts/test_palette_sync.py`
all pass; visually confirmed across live renders (Mumbai, Phoenix,
McMurdo Antarctica, Sittard rain-category) and the crafted degenerate
fixture above. Fresh-context subagent review surfaced and this session
fixed the isothermal-rain-label bug before shipping.

---

### 47. Switch forecast model from best_match to a DWD ICON blend
Branch `forecast-model-blend`

`weather_data.py`'s Open-Meteo forecast request used `models=best_match`,
which resolves to KNMI's own HARMONIE-AROME-Netherlands model for this
project's Sittard location. The sibling Weather-Reader research project ran
a real, backfilled-data comparison of forecast accuracy against Sittard
ground truth (KNMI actuals) and found KNMI's own model came in dead last of
7 candidates - DWD's `dwd_icon_d2`/`dwd_icon_eu` clearly won on nearly every
variable (`MODELING_PLANS.md` Plan 4), a "domain edge effect" from Sittard
sitting near KNMI's Netherlands-grid boundary. That finding was deliberately
left un-acted-on pending a real decision; this entry acts on it.

- `OPEN_METEO_FORECAST_URL` now requests `models=dwd_icon_d2,dwd_icon_eu,best_match`
  (`MODEL_PRIORITY`) in one combined call, instead of `best_match` alone.
- Confirmed live against the real API (not assumed) before implementing:
  DWD's ICON-D2/ICON-EU have much shorter real forecast horizons than this
  project's `forecast_days=7` config (~54h / ~123h respectively) - `best_match`
  stays in the request as the full-horizon backstop for the tail. Open-Meteo
  does not auto-merge a multi-model request - each variable comes back
  suffixed per model (e.g. `temperature_2m_dwd_icon_d2`), but *only* when
  2+ of the requested models are actually valid for the location; a model
  outside its own domain is dropped from the response entirely (key
  absent), and once only one model remains valid there (confirmed for
  Phoenix - any non-European location), Open-Meteo drops suffixing
  altogether and returns the plain unsuffixed key instead. New
  `_merge_model_series`/`_merge_model_blend` walk `MODEL_PRIORITY` per
  (variable, index) and fall back to the plain key, reproducing the exact
  same unsuffixed `{"timezone", "current", "hourly", "daily"}` shape a
  single-model response always had - every existing parser in
  `weather_data.py` needed zero changes.
- The `current` block is never suffixed regardless of model count - Open-Meteo
  sources it from whichever model is listed *first* in `models=` (confirmed
  by swapping order across live calls), so `current` conditions come from
  `dwd_icon_d2` with no extra request or merge code.
- This also makes the fallback self-correcting for every non-Sittard
  location `scripts/test_locations.py` covers: outside DWD's coverage, its
  arrays are absent entirely, so every hour/day falls straight through to
  `best_match` with no special-casing - confirmed all 14 locations render
  identically to before except Sittard itself.
- New `scripts/test_model_blend.py`: 13 deterministic unit tests against
  crafted multi-model-suffixed fixtures, covering the horizon boundaries
  (53/54h, 122/123h), the out-of-domain (all-null-equivalent) case, a
  model's key entirely absent vs. null-filled, the single-valid-model
  plain-key fallback, and `_merge_model_blend`'s `current` passthrough.
- `IDEAS.md`'s "Use a different weather model for the best forecast" line
  removed - built by this entry.

**Active** - current design. Verified: new `scripts/test_model_blend.py`
(13/13), `scripts/test_locations.py` (all 14 locations, all 3 screen
modes - live network, real regression check), `scripts/test_precip_scenarios.py`,
`scripts/test_forecast_rain_scenarios.py`, `scripts/test_forecast_quality_scenarios.py`,
`scripts/test_pollen_scenarios.py`, `scripts/test_display_freshness.py`,
`scripts/test_palette_sync.py` all pass with zero diffs (these monkeypatch
the fetch layer wholesale, unaffected by the merge either way). Fresh-context
subagent review found no correctness bugs. Merged to `main` and deployed:
pulled on the real Pi, forced a real timer tick
(`pi-weather-display.service`, exit 0), confirmed a real end-to-end
fetch -> render -> display cycle on the physical panel.

---

### 48. Pluggable local weather-station seam
Branch `local-station-seam`

`IDEAS.md` had long noted wanting "actual" (not modeled) current
temperature/rain from a local weather station. No station is owned/chosen
yet, so this builds the generic seam (config + fetch/merge contract) rather
than a specific vendor integration, so a real one can be wired in later
without restructuring - same spirit as entry 47's model blend, but for a
seam with nothing on the other end yet.

- New `weather_data.StationConditions` dataclass (`temperature_c`,
  `rain_mm` - the latter a **rate**, mm/h, by documented convention, not an
  accumulation) + `STATION_ADAPTERS` registry (one placeholder entry,
  `"generic_http"` - reads flat JSON from a configured URL, optionally
  bearer-authed) + `_get_station_conditions`, following the exact fail-soft
  pattern already established for the RIVM/luchtmeetnet.nl integration
  (`_get_rivm_current_lki`): every adapter is a one-arg callable that never
  raises, `None`-able per field on partial sensor failure.
- 4 new `DisplayConfig` fields (`station_enabled`, `station_type`,
  `station_base_url`, `station_api_key`), with `settings_store.py`
  validators and web UI form controls (a new "Lokaal weerstation" fieldset
  in `settings.html`) - matches this project's existing invariant that
  every `DisplayConfig` field has a form control.
- `fetch_snapshot` now sources `current_temp` from the station when present
  (else the existing Open-Meteo `current.temperature` fallback);
  `feels_like` stays Open-Meteo-only always (no generic station API
  reliably publishes a computed apparent-temperature figure) - a known,
  documented limitation, not silently glossed over.
- **Current rain has no existing display slot** - the current-conditions
  panel has ~22px of vertical slack left (recently reclaimed by entry 46's
  font bump) and the data-point grid is a fixed 2x3 with no spare cell
  (deliberately fixed at a constant count, per `docs/settings.md`). Per
  explicit user direction, rain is instead reflected by **swapping the main
  weather icon**: new `_apply_station_rain_override` swaps the current icon
  to a rain icon (`"51d"`/`"53d"`/`"09d"` by intensity threshold) only when
  the model's own icon doesn't already depict precipitation
  (`DRY_ICON_KEYS`) - a model that already shows rain/snow/thunderstorm/hail
  is left untouched. Confirmed rain icons have no night variant in this
  codebase's asset set (`docs/icons.md`), so this never produces a
  non-existent `"51n"`/`"53n"`/`"09n"` key.
- New `WeatherSnapshot.current_rain_mm` field (the raw station reading, or
  `None`) - kept even though nothing renders it as text, for the
  icon-override logic and any future display use.
- A fresh-context subagent review caught a real bug in
  `_fetch_station_generic_http`: it only validated the HTTP transport
  (network errors, non-2xx status, unparseable JSON), not the payload's
  shape - a non-dict JSON body raised an uncaught `AttributeError` on
  `payload.get(...)`, and a dict with a wrong-typed field (e.g.
  `{"temperature": "warm"}`) passed the adapter silently but then crashed
  `fetch_snapshot` at `round(station_temp)` with a `TypeError` - both
  reproduced end-to-end, both worse than "station unreachable" since a
  misconfigured/buggy endpoint (not just a down one) would break every
  scheduled render until fixed, contradicting the adapter's own
  must-never-abort contract. Fixed with a new `_coerce_optional_number`
  helper (rejects non-numeric values and `bool`, which is a Python `int`
  subclass and would otherwise silently become `1.0`/`0.0`) plus an
  explicit `isinstance(payload, dict)` check before any `.get()` call.
- New `scripts/test_station_scenarios.py`: 13 deterministic tests against
  crafted fixtures for *both* the Open-Meteo forecast and the station
  adapter (so the model's dry/wet state is controlled, not dependent on
  live weather) - covers the disabled-by-default no-op path, a full
  reading overriding temp+icon, the "already wet, don't override" case, a
  `None`-returning adapter failing soft, partial readings (temp-only,
  rain-only), the exact intensity thresholds, and (added after the review
  above, faking `requests.get` directly to reach `_fetch_station_generic_http`'s
  real parsing path) the non-dict-payload and wrong-typed-field crash
  scenarios. Also renders 3 scenarios (disabled, light rain, heavy rain +
  negative temp) across all 3 screen modes as a visual clipping check - no
  overflow/collision found.
- `IDEAS.md`'s local-station line reworded (not deleted) - the seam exists,
  but no real vendor is chosen yet.

**Active** - current design. Verified: new `scripts/test_station_scenarios.py`
(13/13), full existing suite (`scripts/test_model_blend.py`,
`scripts/test_precip_scenarios.py`, `scripts/test_forecast_rain_scenarios.py`,
`scripts/test_forecast_quality_scenarios.py`, `scripts/test_pollen_scenarios.py`,
`scripts/test_display_freshness.py`, `scripts/test_palette_sync.py`,
`scripts/test_locations.py` - all 14 locations, all 3 screen modes) all
pass with zero diffs (station is inert by default,
`station_enabled=False`). Web UI round-trip verified end-to-end against a
local `web_app.py` instance (save -> persisted to `settings.json` -> reload
reflects it, then reset to defaults). Merged to `main` and deployed:
`pi-weather-web.service` restarted (this entry touches `web/routes.py`,
a persistent process - a plain `git pull` alone wouldn't have picked it
up), then a forced-refresh tick confirmed a real end-to-end
fetch -> render -> display cycle on the physical panel.

---

### 49. Drop the decimal on the shared gridlines' rain value
Branch `fix/gridline-rain-no-decimal`

Per explicit user ask: the rain value shown at the shared temp/rain
gridlines (`"gridlines"`/`"compact"` screen mode, `rain_axis_format="mm"`)
used to share `_format_rain_number` (one decimal, trailing zero dropped)
with the rain axis's own top-extreme label. New `_format_rain_number_int`
(rounds to a whole number, no decimal) is used for the gridline value only
- it's a geometric scale marker derived from the axis's pixel position, not
a real per-hour reading, so a decimal wasn't adding meaningful precision
there. The axis top-extreme label (`_format_rain_number`, a real data
point) is untouched.

**Active** - current design. Verified: `scripts/test_precip_scenarios.py`,
`scripts/test_forecast_rain_scenarios.py`, `scripts/test_forecast_quality_scenarios.py`,
`scripts/test_pollen_scenarios.py`, `scripts/test_display_freshness.py`,
`scripts/test_palette_sync.py`, `scripts/test_model_blend.py`,
`scripts/test_station_scenarios.py`, `scripts/test_locations.py` (all 14
locations, all 3 screen modes) all pass; visually confirmed via
`mock_display_output/precip_scenario_test/rain_gridlines.png` and
`hail_gridlines.png` that gridline rain values now render as plain
integers (e.g. `"3"`, `"2"`, `"4"`) with no decimal point.

---

### 50. Keep the rotated "Regen [mm]" side label in plain mm gridline mode
Branch `feature/mm-mode-keep-rain-side-label`

Entry 45 dropped the rotated precipitation side label entirely whenever a
rain/hail gridline label was drawn (`any_gridline_labeled`), regardless of
`rain_axis_format` - reasonable when the gridline label could be a wide
intensity word ("motrgn"), but entry 49's decimal-drop made the plain
`"mm"`-mode gridline number short enough that real unused width was left in
`RIGHT_MARGIN`. Per explicit user ask, the side label is now kept in `"mm"`
mode (only still dropped in `"category"` mode, where the wide words
genuinely collide with it).

A first pass just flipped the suppression condition and re-showed the label
at its old fixed x offset - visual testing immediately caught a real
overlap: the rotated label spans the plot's **full height**, so any
gridline number landing near the vertical center (e.g. this render's
interior "2" gridline) sat directly underneath the label's text instead of
beside it (see the before/after crop in
`mock_display_output/precip_scenario_test/_debug_crop_rightlabel.png` -
kept as the working record of the bug, not deleted once fixed). Fixed by
measuring the actual rendered width of the widest gridline number drawn in
this render (`max_rain_number_w`, tracked during the existing gridline
loop) and positioning the side label past it (`plot_x1 + 6 + max_rain_number_w + 6`)
instead of a fixed offset - the two columns now sit side by side at every
gridline position, not just by luck of where a given day's numbers happen
to land.

**Active** - current design. Verified: `scripts/test_precip_scenarios.py`,
`scripts/test_forecast_rain_scenarios.py`, `scripts/test_forecast_quality_scenarios.py`,
`scripts/test_pollen_scenarios.py`, `scripts/test_display_freshness.py`,
`scripts/test_palette_sync.py`, `scripts/test_model_blend.py`,
`scripts/test_station_scenarios.py`, `scripts/test_locations.py` (all 14
locations, all 3 screen modes) all pass. Visually confirmed via crafted
rain/hail gridline renders (single- and double-digit gridline numbers) and
a real live rainy location (Mumbai, `location_consistency_test/mumbai_india_gridlines.png`)
that the number and side label no longer overlap at any gridline position,
and that `"category"` mode's existing suppression is unchanged.

---

### 51. Match the rotated precip side label to the axis numbers' size/weight
Branch `feature/precip-side-label-match-axis-font`

Per explicit user ask: the rotated side label ("Regen [mm]" etc.) used
`font_bold` (bold, 14px) - noticeably smaller than the axis/gridline
numbers next to it (`font_axis`, bold, 18px). Switched the `_vertical_text`
call to `font_axis` so both read as one consistent scale.

A real conflict surfaced during testing, not assumed away: the rotated
label's height (post-rotation) is the text's own *pre-rotation width* -
at `font_axis`, `"Sneeuw [cm]"` (the longest of the four `precip_label`
values) needs ~110px, but the plot itself is only ~104px tall, so it
visibly overlapped the top/bottom axis-extreme numbers (confirmed via a
zoomed render crop before concluding anything). `"Regen [mm]"`/
`"Hagel [mm]"`/`"Droog"` all fit within 1px or less - verified directly per
explicit user request to double-check, not assumed from the snow case.
Rather than shrinking every label to accommodate the one outlier (or
accepting a visible defect on snow days), new `_pick_side_label_font`
tries `font_axis` first and falls back to the original `font_bold` only
for whichever label's rotated height would actually exceed the plot - same
shrink-to-fit spirit as `canvas.py`'s existing `_fit_font`/
`widgets/forecast.py`'s own copy, adapted for height instead of width
since the text is rotated.

**Superseded by entry 52's positioning fix for the shrink-to-fit mechanism
specifically** (the font-size match itself is still active) - see that
entry for why, and for a second bug this same font-size bump silently
introduced that entry 51's own testing missed (`"original"` screen mode +
`rain_axis_format="category"`). Original verification, kept for the
record: `scripts/test_precip_scenarios.py`,
`scripts/test_forecast_rain_scenarios.py`, `scripts/test_forecast_quality_scenarios.py`,
`scripts/test_pollen_scenarios.py`, `scripts/test_display_freshness.py`,
`scripts/test_palette_sync.py`, `scripts/test_model_blend.py`,
`scripts/test_station_scenarios.py`, `scripts/test_locations.py` (all 14
locations, all 3 screen modes) all pass. Visually confirmed via zoomed
crops of all four `precip_label` cases (rain/hail/snow/dry, gridlines and
compact) and a real live rainy location (Mumbai) that rain/hail/dry now
render bigger and bolder with no overlap, and that snow correctly falls
back to the smaller font with no overlap either.

---

### 52. Position the side label past axis-extreme numbers instead of shrinking it
Branch `feature/side-label-clear-axis-extremes`

Entry 51's shrink-to-fit fallback (`_pick_side_label_font`) fixed
`"Sneeuw [cm]"` overlapping the top/bottom axis-extreme numbers by
rendering it smaller than the other three precip labels - a real fix, but
one the user pointed out (plan-only request) treated the symptom rather
than the actual cause: the collision is horizontal (the rotated label's
column overlaps the numbers' column at `plot_x1 + 6` vs `plot_x1 + 10`),
not really a size problem, and there was real unused width to the right
that a repositioning could use instead.

**Investigating the plan surfaced a second, independent bug already live
on `main`, not part of what was asked but caught before shipping anything
new**: entry 51's font-size bump also silently broke `"original"`
(non-gridline) screen mode combined with `rain_axis_format="category"`.
The old suppression check
(`show_temp_gridlines and any_gridline_labeled and show_intensity_labels`)
only ever suppressed the side label inside gridlines/compact mode -
`"original"` mode always draws its own axis-extreme label as a wide
intensity word ("licht", "motrgn", up to 60px at the bumped font size) at
the same `plot_x1 + 6` position, unsuppressed, and the side label was
never being suppressed to make room for it there. Confirmed via a real
render before concluding anything (`rain_original_category.png` showed
"Regen" directly overlapping "licht").

**Fix, addressing both**:
- Side label suppression simplified to just `show_intensity_labels` -
  true in every screen mode now, not gated on `show_temp_gridlines`/
  `any_gridline_labeled` - since intensity words are always too wide to
  push the label past without exceeding `RIGHT_MARGIN` and clipping off
  the canvas edge.
- In plain-number mode (the common case), the label is now always shown,
  positioned past the widest NUMBER actually drawn anywhere in the
  right-side column - not just interior gridline values (entry 49/50's
  `max_rain_number_w`) but now also the top/bottom axis-extreme numbers
  (`top_label`/`bottom_label`), whose widths get folded into the same
  accumulator right where they're drawn, respecting the existing
  suppression/`"Droog"`-skip logic already governing whether they draw at
  all.
- With the label now never landing in the same column as a number, entry
  51's shrink-to-fit fallback (`_pick_side_label_font`) is no longer
  needed and was removed - every precip label (including `"Sneeuw [cm]"`)
  now renders at the same consistent `font_axis` size.
- Dead code removed alongside: `any_gridline_labeled` (only used by the
  old suppression check) and the now-unused `font_bold` parameter on
  `render_chart` (only used by the deleted fallback) - `canvas.py`'s call
  site updated to match the narrower signature.
- A fresh-context review flagged, as a side effect rather than a bug: this
  same generalization also closes a latent overlap risk that existed on
  `main` before this entry, in `"original"` + `"mm"` mode with a 2-digit
  `rain_axis_max` (previously positioned at the old fixed `plot_x1 + 10`
  regardless of the axis-extreme number's own width) - not something
  anyone had hit yet, but a real correctness improvement noticed in
  passing, not designed for.

**Active** - current design. Verified: `scripts/test_precip_scenarios.py`,
`scripts/test_forecast_rain_scenarios.py` pass; a fresh-context subagent
review traced every rain-axis-number draw site into `max_rain_number_w`,
confirmed `RIGHT_MARGIN=82`'s budget holds (including a synthetic 2-digit
`"original"`+`"mm"` worst case, rendered not just computed), confirmed no
dangling references to the removed function/parameter/variable anywhere in
the repo, and confirmed `canvas.py`'s call site lines up with the new
signature. Visually re-confirmed via zoomed crops across every
`precip_label` x screen-mode x `rain_axis_format` combination (rain/hail/
snow/dry, original/gridlines/compact, mm/category) plus a real live rainy
location (Mumbai) - the `rain_original_category.png` collision this entry
set out to fix is gone, and every other combination remains collision-free.

---

### 53. Deduplicate the rain axis's number labels
Branch `fix/rain-axis-duplicate-labels`

User report from the real deployed display: the rain axis showed the digit
"1" twice. Root-caused with a real before/after reproduction (not assumed):
on a near-dry day, `rain_axis_max` clamps to the `max(1, ...)` placeholder
floor, and the topmost interior gridline's own `rain_at_y` (close to but
under 1) can round to "1" too - landing far enough in *pixels* from the
axis-extreme label to dodge the existing proximity-based suppression
(`near_max_rain`/`suppress_max_rain_label`, which only checks pixel
distance, not value equality), so both labels drew.

Two fixes, both per explicit user ask:
- **"Drop the maximum if it is the same number"**: new
  `topmost_gridline_rain_label` tracks the topmost interior gridline's own
  label (the loop's last write, since `y_temp(v)` decreases as `v`
  ascends towards `grid_end`). The top axis-extreme label's draw condition
  gained `and top_label != topmost_gridline_rain_label`.
- **"Show decimals when needed [at] the dotted lines"**: a second,
  independent duplicate class - two *adjacent* interior gridlines rounding
  to the same whole number (unrelated to the axis-extreme). New
  `prev_gridline_int_label` tracks each gridline's plain int-rounded value;
  `rain_at_y` is monotonic in `v`, so a same-value collision can only ever
  involve the immediately preceding gridline - checking just that one
  catches every such run without a second pass. On a collision, the
  colliding gridline falls back to a decimal instead of the bare integer.

**A real gap in the decimal fallback, caught by a fresh-context review
before shipping**: the first version of the fallback just called the
existing `_format_rain_number` (one decimal, trailing zero dropped via
`:g`) - but that can itself round right back to the same whole number it
was supposed to disambiguate from (e.g. `0.9902` rounds to `1.0` at one
decimal, and `:g` drops the trailing `.0`, producing `"1"` again -
silently reintroducing the exact duplicate one level down). Fixed with new
`_disambiguate_rain_number`, which escalates from one decimal to two only
if one wasn't enough. A second review pass mapped the function's own
residual limit precisely (a 2,000,000-sample fuzz test found the failure
window is exactly `v` within ±0.005 of the conflicting integer) - narrow
enough, and visually inconsequential enough when hit, to accept rather
than chase with a third decimal place (the same boundary problem recurs
one decimal place down regardless, an asymptotic limit of
round-and-compare disambiguation, not a fixable oversight).

New `scripts/test_chart_axis_labels.py` (5 tests, calls `render_chart`
directly with crafted `HourPoint` lists and spies on `ImageDraw.Draw.text`
to assert no two rain-axis strings are ever identical) - each of the three
bugs above is independently reproduced and locked in as a regression test,
including one found via brute-force search over realistic integer
temperatures (`max_temp=31`, a trace of rain) specifically for the
decimal-escalation case, not just the review's abstract counter-example.

**Active** - current design. Verified: new `scripts/test_chart_axis_labels.py`
(5/5 - each confirmed to genuinely fail against the pre-fix code, not just
pass trivially), `scripts/test_precip_scenarios.py`,
`scripts/test_forecast_rain_scenarios.py`, `scripts/test_forecast_quality_scenarios.py`,
`scripts/test_pollen_scenarios.py`, `scripts/test_display_freshness.py`,
`scripts/test_palette_sync.py`, `scripts/test_model_blend.py`,
`scripts/test_station_scenarios.py`, `scripts/test_locations.py` (all 14
locations, all 3 screen modes) all pass. Two fresh-context subagent review
passes - the first caught the decimal-fallback gap above before it shipped,
the second confirmed the fix's own residual limit is real but acceptable.

---

## Pruned branches

- `real-icons` (was local-only) - fully merged (entry 2) via PR #1, zero
  commits ahead of `main`, purely historical. Deleted 2026-08-09.
- `display-opt` (was local + remote) - zero commits ahead of `main`; its
  content was merged then explicitly reverted in `main`'s own history
  (entry 9). Deleted 2026-08-09, locally and on origin.

`main` is now the only branch, locally and on origin.
