# Plan: crisp text via true bitmap fonts (`PIL.BdfFontFile`/`PcfFontFile`)

Status: **rejected on real hardware** (2026-08-11). Prototyped (Spleen +
Terminus bitmap fonts, including a faked-bold alpha dilation for
Spleen's single weight) and pushed to the actual Inky panel (branch
`text-rendering-bitmap-font-prototype`, never merged - not better than
the current normal Jost rendering, `canvas.py` untouched). Full
prototype/findings on that branch, including the empirically-corrected
detail that `BdfFontFile.to_imagefont()` doesn't exist in this repo's
pinned Pillow (the real API is `BdfFontFile.save()` + `ImageFont.load()`).
See also
[text-rendering-option-1-fontmode.md](./text-rendering-option-1-fontmode.md)
(also rejected) and `TODO.md`'s Fonts & text section for the full
picture, including a third avenue (new TrueType fonts) tried afterward.

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
`text-rendering-alternatives-research`) alongside three others - PIL's
native monochrome rasterization (see the sibling plan doc), headless
Chromium/CSS (dropped: already a deliberately-rejected architecture, the
upstream `fatihak/InkyPi` this project forked from still works this way,
but a Pi Zero W can't run headless Chromium comfortably), and switching
away from the Jost font entirely for a better-hinted TrueType alternative
(dropped: no candidate identified, and it would change the app's visual
identity rather than just its rendering pipeline - this option below
*also* changes the typeface, but with much stronger prior-art backing,
see below).

## Current font sizes in use (for reference)

Confirmed via `grep -n 'assets\.font(' canvas.py widgets/*.py`: 11, 13,
14, 15, 18, 22, 24, 64 (fixed call sites), plus
`WeatherCanvas._fit_font`'s dynamic shrink range (steps of 2 from 24 or
20 down to a floor of 12), plus `widgets/forecast.py`'s dynamic
`max(10, region.w * 0.15)`. Two weights throughout: "normal" (Jost.ttf)
and "bold" (Jost-SemiBold.ttf).

## What this option is

Hand-designed, pre-rasterized pixel glyphs (BDF/PCF font files, the
classic X11 bitmap font format) loaded via Pillow's own
`BdfFontFile`/`PcfFontFile` -> `to_imagefont()` (or the legacy
`pilfont.py`-generated `.pil`/`.pbm` pair + `ImageFont.load()`) - not a
scalable vector outline rendered at runtime at all. No antialiasing
exists to harden in the first place; every pixel was placed by a human
(or a very deliberate font-design process) specifically for that exact
pixel grid.

## Why it might help - strongest prior-art backing of any option researched

This is exactly what the **Weather-EPS32S3 sibling project already
does**, targeting this exact same physical panel family (Pimoroni
AC073TC1A 7.3" ACeP) - it uses u8g2's pre-rasterized bitmap font tables
via `U8g2_for_Adafruit_GFX`, with documented rationale
(`README.md:316-324`, `src/assets/asset_store.h:6-20` in that repo) that
boils down to exactly this: bitmap fonts sidestep the
antialiasing-hardening problem entirely. Adafruit's own "Preparing
Graphics for E-Ink Displays" guidance independently agrees: disable
smoothing, bitmap fonts work well when pixels map 1:1 to the display.

## Why it might not / real costs

- **Discrete sizes only.** A BDF font ships in specific fixed pixel sizes
  (e.g. Spleen: 5x8/6x12/8x16/12x24/16x32/32x64; Terminus similar fixed
  steps). This app currently uses 8+ distinct sizes freely (any integer,
  since TrueType scales smoothly) - matching them means either snapping
  every call site to the nearest available bitmap size (touching
  `layout.py`'s tuned pixel math in multiple places) or only replacing
  the specific problem sizes (~18-24px bold) and leaving everything else
  as TrueType+harden, a hybrid with two different text rendering paths
  in one app.
- **Bold weight isn't guaranteed.** Many free bitmap fonts ship one
  weight only, unlike Jost's normal/SemiBold pair this app relies on
  throughout. Mitigation: this project already has a pixel-dilation
  utility built for exactly this problem shape -
  `widgets/icons.py:12-53`'s `thicken_icon()` (dilates an icon's alpha
  channel to fake a bolder stroke without antialiasing) - the same
  technique could plausibly fake "bold" from a single-weight bitmap font
  by dilating its rendered glyph mask, worth prototyping rather than
  assuming a bold variant must exist.
- **Visual identity change.** Unlike Option 1 (same Jost typeface, just a
  different rasterization mode), this replaces the actual typeface for
  at least some text - a real aesthetic decision, not just a pipeline
  tweak, and needs explicit sign-off independent of the technical
  comparison.
- **New asset + licensing.** Needs a chosen BDF font file added to the
  repo and a new `docs/attribution.md` entry (matching how Jost's own
  license is presumably already documented there) - unlike Option 1's
  zero new dependencies.

## Implementation steps

1. **Scope the prototype narrowly first** - don't attempt an app-wide
   font swap as the first step. Pick 1-2 candidate BDF fonts with a size
   near the actual problem range (~24px - e.g. Spleen's 12x24, or
   Terminus's closest step), confirm license compatibility for
   `docs/attribution.md`, and build the same side-by-side comparison
   tool pattern as Option 1 (`scripts/text_bitmap_font_compare.py`), but
   only for the specific flagged case (e.g. "Matig Gras" at the bitmap
   font's native size) rather than every app size at once, since a
   bitmap font can't render at other sizes anyway.
2. Wire the loading path: `PIL.BdfFontFile.BdfFontFile(fp).to_imagefont()`
   (confirm this Pillow API works in the exact Pillow version this repo
   currently pins, not just in current docs) as a new
   `AssetStore.bitmap_font(name)` method (no `size_px` parameter, unlike
   `.font(weight, size_px)` - a fixed-size font has no scaling concept) -
   additive, doesn't touch the existing `.font()` path.
3. Render locally, sanity-check via `panel_sim.py`, push to the real
   display, **get a real-hardware verdict before deciding anything about
   scope**.
4. If it looks better: decide scope (which specific sizes/call sites end
   up replaced - likely just the ~18-24px bold cases that actually
   showed the problem, given the size-matching cost above) and whether
   faking bold via `thicken_icon`-style dilation is needed and looks
   acceptable.
5. Regression suite + docs: `docs/attribution.md` (new font license
   entry), `docs/icons.md`/`docs/settings.md` (note the new rendering
   path and which sizes use it), `TODO.md` update, `docs/changes.md` new
   entry.

## Critical files

- `widgets/icons.py` - new `AssetStore.bitmap_font()` alongside the
  existing `.font()` (`widgets/icons.py:119-126`); `thicken_icon()`
  (`widgets/icons.py:12-53`) as a possible fake-bold technique to reuse
- `canvas.py` - whichever specific call sites end up switched (scope
  decided after the real-hardware verdict, not upfront)
- `docs/attribution.md` - new font's license entry
- New `scripts/text_bitmap_font_compare.py`
- New font asset under `assets/fonts/` (exact file TBD - candidate
  selection is step 1)

## Verification

1. `python scripts/text_bitmap_font_compare.py --mock-output <path>`
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
