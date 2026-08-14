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

### 33. Forecast cards: rain amount + weather-quality border color
Branch `feature/forecast-rain-quality-cards`

Two additions to the multi-day forecast row, requested together since
both need the same new daily-precipitation data: (1) the expected rain
amount ("3mm", "0.6mm") drawn next to each day's icon, only when rain is
actually expected; (2) each card's border colored by how pleasant that
day's weather is overall (temperature + precipitation combined), using
the same worst-of-both-wins `max()` idiom entry 32's "Kwaliteit & Pollen"
gauge already established. See [settings.md](./settings.md)'s new
"Forecast cards" section for the full tier tables.

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

**Active** - current design. Verified: `scripts/test_forecast_quality_scenarios.py`
(new, 12 scenarios - every tier, both boundary edges exactly at 0.2mm/26°C,
the two inputs disagreeing in opposite directions, the mm-text on/off
gate); a full 14-location `scripts/test_locations.py` regression (no
crashes, run twice - before and after the review fixes); direct visual
checks of a real live render (a 36°C day correctly red, rainy days
correctly yellow/orange with sensible mm amounts next to real rain-cloud
icons), the `forecast_days=10` + `show_moon_phase=True` tight-layout case
that caught the first overflow bug, and `forecast_days=12` (the review's
own flagged case) confirming the text now omits cleanly instead of
overflowing; and the exact boundary values (-0.3°C, -5.7°C) the review
traced through `_temp_quality_tier` by hand to confirm the truncation fix.

### 34. Forecast-card quality tiers move to an editable weather_quality.toml
Branch `feature/forecast-quality-border-color`

Entry 33's temperature/precipitation ranges and colors were hardcoded
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

---

## Pruned branches

- `real-icons` (was local-only) - fully merged (entry 2) via PR #1, zero
  commits ahead of `main`, purely historical. Deleted 2026-08-09.
- `display-opt` (was local + remote) - zero commits ahead of `main`; its
  content was merged then explicitly reverted in `main`'s own history
  (entry 9). Deleted 2026-08-09, locally and on origin.

`main` is now the only branch, locally and on origin.
