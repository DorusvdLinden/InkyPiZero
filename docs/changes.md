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

**Active** - current design. Known permanent limitations, tracked in
`TODO.md`: pollen's contribution is Europe-only/seasonal (an Open-Meteo
data limitation, not a bug, falls back to AQI alone or "N/A"), and
Open-Meteo/CAMS models fewer herb/weed species than Dutch pollen services
track (confirmed against pollennieuws.nl's broader "Kruiden" category).

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
both hold steady. The 10-minute/1-hour cadence is hardcoded, not exposed
as a setting.

---

### 24. Wire `PALETTE` to `config.inky_saturation` — most recent
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

---

## Pruned branches

- `real-icons` (was local-only) - fully merged (entry 2) via PR #1, zero
  commits ahead of `main`, purely historical. Deleted 2026-08-09.
- `display-opt` (was local + remote) - zero commits ahead of `main`; its
  content was merged then explicitly reverted in `main`'s own history
  (entry 9). Deleted 2026-08-09, locally and on origin.

`main` is now the only branch, locally and on origin.
