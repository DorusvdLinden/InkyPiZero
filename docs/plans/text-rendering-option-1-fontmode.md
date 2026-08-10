# Plan: crisp text via PIL's native monochrome rasterization (`fontmode="1"`)

Status: **proposed, not implemented**. One of two candidate fixes for
jagged text on the e-paper panel - see also
[text-rendering-option-2-bitmap-fonts.md](./text-rendering-option-2-bitmap-fonts.md).
Neither has been chosen yet.

## Context

Bold text in the ~18-24px range (e.g. "Matig", data-point values, the
date header) shows visible stair-stepped curves on the real Inky
Impression 7.3" panel. `display/quantize.py`'s pipeline renders text
antialiased (PIL/FreeType's default), then `harden_neutral_pixels()`
snaps antialiased edge pixels to a hard black/white decision by luminance
threshold, then quantizes with no dithering - the right call for icons
and chart lines (which was the original reason this design exists - see
`TODO.md`'s Color palette & quantization section), but at 18-24px this
post-hoc hardening heuristic doesn't have enough information to place
curve edges well.

**Already tried and rejected** (branch `supersampled-text-compare`,
deleted, 2026-08-10): rendering glyphs at 4x then downsampling with
LANCZOS before compositing. Looked smoother in isolated digital
comparisons, but looked *worse* on the real panel - most likely because
it discards the font's own size-specific TrueType hinting. Full writeup
in `TODO.md`'s Fonts & text section; don't repeat this specific approach.

**This option researched** 2026-08-10 (branch
`text-rendering-alternatives-research`) alongside three others - true
bitmap fonts (see the sibling plan doc), headless Chromium/CSS (dropped:
already deliberately rejected architecture, the upstream `fatihak/InkyPi`
this project forked from still works this way, but a Pi Zero W can't run
headless Chromium comfortably), and switching away from the Jost font
entirely (dropped: no better-hinted candidate font identified, and it
would change the app's visual identity rather than just its rendering
pipeline).

## Current font sizes in use (for reference)

Confirmed via `grep -n 'assets\.font(' canvas.py widgets/*.py`: 11, 13,
14, 15, 18, 22, 24, 64 (fixed call sites), plus
`WeatherCanvas._fit_font`'s dynamic shrink range (steps of 2 from 24 or
20 down to a floor of 12), plus `widgets/forecast.py`'s dynamic
`max(10, region.w * 0.15)`. Two weights throughout: "normal" (Jost.ttf)
and "bold" (Jost-SemiBold.ttf).

## What this option is

`ImageDraw.Draw.fontmode` is a real, already-available PIL attribute
(default `"L"`, antialiased). Setting it to `"1"` before a
`draw.text(...)` call tells FreeType to rasterize the glyph outline
directly into a hard black/white bitmap at the target size - a real
per-vector-edge decision made by FreeType's own mono rasterizer, not a
luminance-threshold guess applied *after* the fact to already-blended
pixels the way `harden_neutral_pixels` works today. Zero new
dependencies, one attribute toggle, same font files, same everything else
in the pipeline.

## Why it might help

`harden_neutral_pixels` is inferring what a blended gray edge pixel
"should" have been; `fontmode="1"` never produces a blended pixel in the
first place, so the pipeline stops relying on that inference for text
specifically. FreeType's mono rasterizer is a purpose-built, mature code
path (not a guess), and still respects the font's hinting instructions
during rasterization (unlike the rejected supersampling approach, which
threw hinting away entirely by rendering at a size the font was never
hinted for).

## Why it might not

FreeType's mono rendering is a cruder decision than antialiased-then-
well-tuned-hardening *can* be in principle - there's a real chance it
looks blockier rather than smoother, just blocky in a different, more
"the font's own hinting decided this" way. This is exactly why it needs
real-hardware validation, not just theoretical confidence - a digital
comparison already proved misleading once this session (the rejected
supersampling attempt).

## Implementation steps

1. **Prototype/comparison first** - new `scripts/text_fontmode_compare.py`,
   structurally identical to the deleted `text_supersample_compare.py`
   (same representative samples: `("bold", 24, "Matig Gras")`, `("bold",
   22, "Maandag augustus")`, `("normal", 18, "Vochtigheid")`, `("bold",
   20, "Zeer slecht")`), rendering "Normaal" (current: default
   `fontmode`) on the left half of the canvas and `fontmode="1"` on the
   right half, both through the full real `quantize_for_panel()`
   pipeline. Confirm empirically whether `draw.fontmode = "1"` can be
   toggled per-call on a shared `ImageDraw.Draw` instance (reset to
   `"L"` afterward) without side effects on later calls - expected to
   work since it's a plain instance attribute read at `text()` call
   time, but verify rather than assume.
2. Render locally (`--mock-output`), sanity-check via
   `scripts/panel_sim.py`, then push directly to the real Pi display
   (same pattern as the rejected prototype - `InkyDriver` when
   `--mock-output` isn't passed).
3. **Stop and get a real-hardware verdict before proceeding** - this is
   the step that caught the supersampling regression; do not skip it or
   trust the local/digital preview alone.
4. If it looks better: decide scope (every `assets.font()` call site, or
   only the bold/18px+ sizes where the problem was actually observed -
   the small 11-15px text was never flagged as visibly jagged, so
   defaulting to "everywhere" isn't obviously correct). Implement as a
   small `WeatherCanvas` helper (e.g. a thin `_draw_text_mono(draw, xy,
   text, font, fill, anchor)` that toggles `fontmode` around a plain
   `draw.text()` call) - much simpler than the deleted supersampling
   helper, no new canvas/compositing logic needed.
5. Rerun the standing regression suite (`test_locations.py`,
   `test_precip_scenarios.py`, `test_pollen_scenarios.py`) - expect zero
   functional diffs (this only touches rendering, not data), but confirm
   no exceptions/crashes across all 14 locations and 3 screen modes.
6. Docs: `docs/icons.md` (note the mono rendering choice near
   `AssetStore.font()`), `TODO.md` (close out or update the Fonts & text
   entry with the real verdict either way - "worked, adopted" or "tried,
   still not better, here's why"), `docs/changes.md` new entry.

## Critical files

- `canvas.py` - every `draw.text(...)` call site (`_draw_header`,
  `_draw_current_conditions`, `_draw_data_points`,
  `_draw_compact_cell_icon_left`, `_draw_compact_cell_icon_above`)
- `widgets/forecast.py` - forecast-card date/day-abbreviation text
- `display/quantize.py` - unchanged, but confirms `harden_neutral_pixels`
  should be a safe no-op on already-binary pixels (worth a quick sanity
  check, not just an assumption)
- New `scripts/text_fontmode_compare.py`

## Verification

1. `python scripts/text_fontmode_compare.py --mock-output <path>`
   locally, then `python scripts/panel_sim.py <raw> <simulated> 0.0` to
   preview the real hardware quantization before spending a hardware
   round-trip.
2. Push the comparison directly to the real Pi display (`git pull` on
   the Pi, run the compare script without `--mock-output` via the
   deployed venv python) - the step that caught the supersampling
   regression the digital comparison completely missed. Do not skip this
   or consider the option validated from the local preview alone.
3. Only after a positive real-hardware verdict: wire into `canvas.py`
   for real, then run the full standing regression suite
   (`scripts/test_locations.py`, `scripts/test_precip_scenarios.py`,
   `scripts/test_pollen_scenarios.py`) to confirm no crashes/regressions
   across all 14 locations and 3 screen modes.
4. Force a final render on the real Pi (`sudo systemctl start
   pi-weather-display.service`) and get explicit confirmation the actual
   weather display (not just the comparison screen) looks right before
   merging.
