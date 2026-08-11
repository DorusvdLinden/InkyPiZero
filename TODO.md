# pi_weather_display - known issues & ideas

Running list of things found during development/testing that aren't fixed yet.
Add to this whenever something rough turns up; check items off (don't delete
them) once fixed. Grouped by area, open items first in each group. See also
`docs/settings.md`, `docs/icons.md`, and `docs/changes.md` for the broader
reference docs this list feeds into.

## Color palette & quantization

- [x] ~~`widgets/palette.py`'s `PALETTE` singleton isn't wired to `config.py`~~ Fixed: `PALETTE.set_saturation(config.inky_saturation)` now runs at the top of both real rendering entry points (`canvas.py`'s `WeatherCanvas.__init__`, `setup_screen.py`'s `render_setup_screen`), keeping every widget color synced to whatever `inky_saturation` is actually configured instead of a hardcoded `0.0`. See `docs/plans/palette-saturation-sync-fix.md` and `scripts/test_palette_sync.py`.

## Icons

- [ ] **`02d`/`02n` icon keys are dead**: `scripts/generate_icons.py` still generates `assets/icons/02d.png`/`02n.png`, and `map_weather_code_to_icon`'s night-remap dict still has entries for them, but the day-mapping side of that function never actually outputs `"02d"` - WMO codes 1/2 map straight to the `022d` composite instead. Either find a real use for these two icons or remove the dead entries/generation. Found while writing `docs/icons.md`.
- [ ] **No hail-specific icon**: WMO thunderstorm-with-hail codes (96/99) share the plain-thunderstorm `11d` icon - only the chart's precipitation axis label (`precip_label`, "Hagel [mm]") distinguishes hail from an ordinary storm; the hourly icon strip does not. Found while writing `docs/icons.md`.
- [ ] **Create dedicated hail icons**: erikflowers/weather-icons has `wi-hail`/`wi-day-hail`/`wi-night-alt-hail` source SVGs (confirmed available, not yet used by `scripts/generate_icons.py`) - add day/night entries (e.g. `96d`/`96n`) the same way the other single-color icons are generated, then map WMO codes 96/99 to them in `map_weather_code_to_icon` instead of falling through to `11d`. Resolves the gap above.
- [ ] **Verify forecast-card moon phase isn't off by one day**: `_parse_forecast()` (`weather_data.py`) computes each forecast card's moon phase for `target_date = dt.date() + timedelta(days=1)` - one day ahead of the card's own date. Presumably intentional (matching "phase for the night that date's forecast covers") but never explicitly verified against a real calendar/reference. Found while writing `docs/icons.md`.
- [ ] 71d/73d/77d (light/moderate snow/snow-grains) all render as the exact same icon (`wi-day-snow`) - weather-icons doesn't have graduated snow-intensity variants the way the old per-condition Flaticon set implied. Similarly 51d/53d/09d (light/moderate/heavy rain) use different source icons but look very similar at small render sizes. Not wrong, just less differentiated than before.
- [ ] `wi-night-clear` (icon `01n`) renders as a noticeably thinner/paler crescent than the `wi-moon-*` family used for moon phases - same fill color, different path weight in the source SVG. Cosmetic only.

## Fonts & text

- [ ] **Missing font glyph fallback**: `AssetStore.font()` only loads Jost.ttf/Jost-SemiBold.ttf, which have no CJK (or other non-Latin) glyphs. When a location name comes back in a non-Latin script (e.g. Tokyo's Nominatim result), PIL silently drops the unsupported characters instead of rendering anything - the header ends up with a blank gap where the city name should be. The old Chromium/CSS renderer didn't hit this because browsers do automatic per-character font fallback; Pillow's single-TTF loader doesn't. Found via `mock_display_output/pi_zero/pi_zero_render_tokyo_japan.png`. Fix likely needs a bundled fallback font (broad Unicode coverage) tried per-character when Jost can't render something.
- [ ] **Bold text ~18-24px (e.g. "Matig", data-point values) shows visible
  stair-stepped curves on real hardware** - the display's quantization
  (`display/quantize.py`) hardens antialiased edges to a hard black/white
  decision with no dithering, the right call for icons/chart lines, but
  leaves jagged curves on text in this size range. **Tried and rejected**
  (branch `supersampled-text-compare`, not merged, 2026-08-10): rendering
  glyphs at 4x then downsampling with LANCZOS before compositing looked
  smoother in isolated digital PNG-crop comparisons, but on the *real*
  panel looked worse, not better - most likely because it discards the
  font's own size-specific TrueType hinting (which snaps stems/curves to
  the pixel grid for crisp small-size rendering) in favor of a generic
  downscale blend. Also cost meaningfully more CPU per label. Don't
  re-attempt supersampling without addressing the hinting-loss problem
  specifically.

  **Researched alternatives (2026-08-10)**: two viable candidates fully
  written up as standalone plan docs, neither implemented or chosen yet -
  [docs/plans/text-rendering-option-1-fontmode.md](./docs/plans/text-rendering-option-1-fontmode.md)
  (PIL's built-in `fontmode="1"` native monochrome rasterization - zero
  new dependencies, cheapest to try) and
  [docs/plans/text-rendering-option-2-bitmap-fonts.md](./docs/plans/text-rendering-option-2-bitmap-fonts.md)
  (true bitmap fonts via `BdfFontFile`/`PcfFontFile` - what the
  `Weather-EPS32S3` sibling project already does on this same physical
  panel, and what Adafruit's own e-ink guidance recommends, at the cost
  of a new font asset and a real visual-identity change). Headless
  Chromium/CSS and switching to a different TrueType font were both
  researched and dropped - see either plan doc's Context section for why.

## Display refresh cadence

- [ ] **Deliberate tradeoff: slower-changing data can go stale on the
  physical display (up to `force_refresh_max_stale_minutes`, default 1h)
  even though the underlying fetch happens every 10 min** -
  `display_freshness.py` only forces a real panel refresh when the main
  icon/temperature changes, or that window has elapsed. If the icon and
  temp both happen to hold steady, forecast cards/the hourly chart/
  humidity/wind/etc. can all be that old on-screen despite fresh data
  existing. Confirmed as the intended behavior (2026-08-10), not a bug -
  documented in `docs/settings.md`.

## WiFi & web UI

- [ ] **No SSID rename**: `wifi_manager.edit_network()` can only update a saved network's password/priority - the con-name and SSID are set together at creation, so a changed SSID needs remove + re-add rather than an in-place rename. Documented in the `/wifi` page copy and `docs/networking.md`, not fixed.
- [ ] **No periodic reconnect check**: `web_app.py`'s connectivity check (activate the setup AP if nothing's reachable) only runs once, at `pi-weather-web.service` startup - if a previously-good station connection drops later at runtime (router reboot, moved out of range), the device stays disconnected until the service is manually restarted rather than automatically falling back to the setup AP. Deliberately out of v1 scope - see the plan's Phase 8.
- [ ] **No real captive-portal DNS redirect** on the setup AP - joining it and opening any URL doesn't auto-redirect to the setup page like commercial IoT devices do; the user has to know/read the exact URL (`http://192.168.4.1`) shown on the e-paper display and type it manually. `dnsmasq-base` (already a dependency) could serve wildcard DNS for this later.
- [ ] **No authentication anywhere in the web UI** - settings edits, WiFi credential changes, and shutdown are all reachable by anyone who can reach the device's IP or join its setup AP. Deliberate, matches button A's existing unauthenticated physical shutdown and the project's trusted-LAN-only threat model - documented explicitly in `docs/networking.md`, not an oversight, but would need revisiting if this device is ever exposed beyond a home LAN.
- [ ] No QR code on the setup screen (would encode `WIFI:S:<ssid>;T:WPA;P:<password>;;` for one-tap phone connect) - would need a new `qrcode` dependency and more rendering work, scoped out of v1.

## Screen modes

- [x] **`compact_style` was never decided on**: committed to `icon_left` (2026-08-11) after comparing fresh renders of all three - `icon_above` left an awkward whitespace gap between icon and text, `icon_above_row` didn't clearly beat `icon_left`. Removed `icon_above`/`icon_above_row`, the `compact_style` parameter (`canvas.py`, `main.py`'s `--compact-style` flag), and the now-dead `layout.data_point_cell_1x4`.

## Kwaliteit & Pollen (combined AQI + pollen)

- [ ] **Pollen's contribution is permanently Europe-only and seasonal** -
  not a bug, a real limitation of Open-Meteo's air-quality pollen data
  (null outside a species' active season, and outside Europe entirely).
  Most non-European renders, and any European one out of season, fall back
  to AQI alone (or "N/A" if AQI is also unavailable). Documented in
  `docs/settings.md`.
- [ ] **Open-Meteo/CAMS only models 6 pollen species, fewer than Dutch
  pollen services track** - confirmed against pollennieuws.nl 2026-08-10:
  it rates "Kruiden" (herbs/weeds) "Zeer ongunstig" (very unfavorable)
  while this app's mugwort+ragweed readings were low/zero the same day.
  Dutch services' "Kruiden" bucket commonly includes weeds Open-Meteo
  doesn't model at all (e.g. nettle/brandnetel, sorrel/zuring,
  plantain/weegbree), so this app's pollen contribution can genuinely
  understate a Netherlands-focused service's even when both are working
  correctly. Not fixable without a different upstream data source -
  documented as a known gap, not a bug. See `docs/settings.md`.
- [ ] **Combined scale is a fresh 4-tier design (Goed/Matig/Slecht/Zeer
  slecht), not identical to either input's own vocabulary** - confirmed
  with the user 2026-08-10 as the preferred option over reusing AQI's 6
  tiers or pollen's 4 outright. Worth revisiting if the combined wording
  ever feels redundant next to AQI's/UV's own tier vocabulary shown
  elsewhere on the same screen.

## General polish

- [ ] All fonts, gauge sizes, and region positions in `layout.py` are a first-pass approximation of `weather.css`'s proportions, not pixel-matched to the original design yet.
