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

### 20. Dynamic precipitation axis label (rain/hail/snow/dry) — most recent
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

---

## Leftover branches worth pruning

- `real-icons` (local) - fully merged (entry 2) via PR #1, zero commits
  ahead of `main`. Safe to delete, purely historical.
- `display-opt` (local + remote) - zero commits ahead of `main`; its content
  was merged then explicitly reverted in `main`'s own history (entry 9).
  Stale, safe to delete.
