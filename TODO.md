# pi_weather_display - known issues & ideas

Running list of things found during development/testing that aren't fixed yet.
Add to this whenever something rough turns up; check items off (don't delete
them) once fixed.

## Bugs

- [ ] **Missing font glyph fallback**: `AssetStore.font()` only loads Jost.ttf/Jost-SemiBold.ttf, which have no CJK (or other non-Latin) glyphs. When a location name comes back in a non-Latin script (e.g. Tokyo's Nominatim result), PIL silently drops the unsupported characters instead of rendering anything - the header ends up with a blank gap where the city name should be. The old Chromium/CSS renderer didn't hit this because browsers do automatic per-character font fallback; Pillow's single-TTF loader doesn't. Found via `mock_display_output/pi_zero/pi_zero_render_tokyo_japan.png`. Fix likely needs a bundled fallback font (broad Unicode coverage) tried per-character when Jost can't render something.
- [x] ~~Fresh-install `libopenblas.so.0: cannot open shared object file` crash on first real render (`inky` -> `numpy` import chain).~~ Fixed: `install/debian-requirements.txt` was missing `libopenblas0`, which numpy's compiled extensions need at import time; only surfaces the first time `display/inky_driver.py` actually imports `inky` on real hardware, since the Windows/`--mock-output` dev path never touches that import. Added `libopenblas0` to the apt requirements.
- [x] ~~Fresh-install `RuntimeError: No EEPROM detected! You must manually initialise your Inky board.` from `inky.auto.auto()` even with a correctly-connected 7.3" Inky Impression.~~ Fixed: `install/install.sh`'s `enable_interfaces()` only ever enabled SPI; the Inky's auto-detect EEPROM lives on I2C, which was left disabled (`dtparam=i2c_arm=on` commented out in `/boot/firmware/config.txt`), so `auto()` had no bus to read. `enable_interfaces()` now also runs `raspi-config nonint do_i2c 0` alongside the existing SPI step.
- [x] ~~Chart: solid blue band across the whole bottom, looked like "the area below the chart isn't connected" + "tick marks too thick".~~ Fixed: the rain-bar highlight-cap rectangle was drawn at a fixed height regardless of the actual bar height, so on hours with ~0 rain it still drew a solid strip - across ~24 hourly columns that reads as one continuous false floor. `widgets/chart.py` now skips drawing a bar entirely when `rain < rain_axis_max * 0.03`.
- [x] ~~Chart icon strip: icons didn't line up with each other (inconsistent size/vertical position between sun/cloud/moon icons).~~ Fixed: source icon PNGs have wildly inconsistent transparent padding within their 512x512 canvas (content height ranges from 352px to 468px depending on the icon), so a uniform resize made some icons look bigger or shifted relative to others. `AssetStore.icon()` now crops to the actual content bounding box first, then scales-to-fit and centers within the requested size, for every icon usage (current icon, forecast cards, chart strip).
- [x] ~~Weather condition/moon-phase/sunrise-sunset icons were individually sourced from different Flaticon authors (see attribution.md history), which is what caused the inconsistent-padding bug above in the first place - `AssetStore`'s crop-and-fit only compensated for it, didn't remove the root cause.~~ Fixed at the source: replaced with recolored PNGs rendered from [erikflowers/weather-icons](https://github.com/erikflowers/weather-icons) SVGs, a single coherent icon set with a consistent `viewBox="0 0 30 30"` per icon. See "Regenerating icons" below.

## Polish / not pixel-tuned yet

- [x] ~~Humidity drop icon shape is a bit chunky/merged where the drops touch in the top row (ellipse+triangle approximation of the original teardrop SVG path) - could look cleaner.~~ Fixed for good by giving up on drawing the shape at all: two hand-drawn Pillow attempts (ellipse+triangle, then a single teardrop polygon) both still looked rough. Now uses `assets/icons/humidity_drop_filled.png` / `humidity_drop_empty.png`, two small transparent PNGs cropped directly out of a pi4-app (the original Chromium/CSS renderer) screenshot (`mock_display_output/icon_overviews/humidity_5drop_options.png`) via connected-component analysis, then pasted per-drop in `draw_humidity_drops` instead of drawn with `ImageDraw`. Pixel-identical to the original design, no seams, no overlap tuning needed.
- [ ] All fonts, gauge sizes, and region positions in `layout.py` are a first-pass approximation of `weather.css`'s proportions, not pixel-matched to the original design yet.
- [ ] Chart's hourly icon strip can overflow slightly past the bottom edge of `CHART_AREA` (~4px) depending on content.
- [ ] Imperial/standard unit rendering (rain axis label, temperature conversion) has only been tested with metric units so far.
- [ ] 71d/73d/77d (light/moderate snow/snow-grains) all render as the exact same icon (`wi-day-snow`) - weather-icons doesn't have graduated snow-intensity variants the way the old per-condition Flaticon set implied. Similarly 51d/53d/09d (light/moderate/heavy rain) use different source icons but look very similar at small render sizes. Not wrong, just less differentiated than before.
- [ ] `wi-night-clear` (icon `01n`) renders as a noticeably thinner/paler crescent than the `wi-moon-*` family used for moon phases - same fill color, different path weight in the source SVG. Cosmetic only.

## Regenerating icons

Weather condition/moon-phase/sunrise-sunset icons in `assets/icons/` are generated
by `scripts/generate_icons.py`, not hand-drawn or downloaded individually - see
`docs/attribution.md` for the source project. To regenerate (e.g. after changing a
color or picking a different source icon):

1. `git clone https://github.com/erikflowers/weather-icons.git` next to this repo
   (or edit `SVG_DIR` in the script to point wherever you cloned it)
2. `pip install resvg-py` (dev-only tool, not an app dependency - pure-Rust SVG
   renderer, no system Cairo needed, unlike `cairosvg` which doesn't work out of
   the box on Windows)
3. `python scripts/generate_icons.py`
