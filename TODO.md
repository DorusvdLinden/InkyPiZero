# pi_weather_display - known issues & ideas

Running list of things found during development/testing that aren't fixed yet.
Add to this whenever something rough turns up; check items off (don't delete
them) once fixed. Grouped by area, open items first in each group. See also
`docs/settings.md`, `docs/icons.md`, and `docs/changes.md` for the broader
reference docs this list feeds into.

## Icons

- [ ] **`02d`/`02n` icon keys are dead**: `scripts/generate_icons.py` still generates `assets/icons/02d.png`/`02n.png`, and `map_weather_code_to_icon`'s night-remap dict still has entries for them, but the day-mapping side of that function never actually outputs `"02d"` - WMO codes 1/2 map straight to the `022d` composite instead. Either find a real use for these two icons or remove the dead entries/generation. Found while writing `docs/icons.md`.
- [ ] **No hail-specific icon**: WMO thunderstorm-with-hail codes (96/99) share the plain-thunderstorm `11d` icon - only the chart's precipitation axis label (`precip_label`, "Hagel [mm]") distinguishes hail from an ordinary storm; the hourly icon strip does not. Found while writing `docs/icons.md`.
- [ ] **Create dedicated hail icons**: erikflowers/weather-icons has `wi-hail`/`wi-day-hail`/`wi-night-alt-hail` source SVGs (confirmed available, not yet used by `scripts/generate_icons.py`) - add day/night entries (e.g. `96d`/`96n`) the same way the other single-color icons are generated, then map WMO codes 96/99 to them in `map_weather_code_to_icon` instead of falling through to `11d`. Resolves the gap above.
- [ ] **Verify forecast-card moon phase isn't off by one day**: `_parse_forecast()` (`weather_data.py`) computes each forecast card's moon phase for `target_date = dt.date() + timedelta(days=1)` - one day ahead of the card's own date. Presumably intentional (matching "phase for the night that date's forecast covers") but never explicitly verified against a real calendar/reference. Found while writing `docs/icons.md`.
- [ ] 71d/73d/77d (light/moderate snow/snow-grains) all render as the exact same icon (`wi-day-snow`) - weather-icons doesn't have graduated snow-intensity variants the way the old per-condition Flaticon set implied. Similarly 51d/53d/09d (light/moderate/heavy rain) use different source icons but look very similar at small render sizes. Not wrong, just less differentiated than before.
- [ ] `wi-night-clear` (icon `01n`) renders as a noticeably thinner/paler crescent than the `wi-moon-*` family used for moon phases - same fill color, different path weight in the source SVG. Cosmetic only.




## Display & hardware

- [ ] **Blank-before-shutdown screen has a mild sprinkling of black dots on real hardware, not just solid white** - investigated (2026-08-12): rendered a synthetic pure-white image through the exact same `quantize_for_panel()` pipeline `blank_and_shutdown()` uses, at both `saturation=0.5` (the old hardcoded bug above) and `0.0` (the real configured default) - both produced a perfectly uniform single-color output, zero stray pixels. Rules out the software quantization pipeline as the cause. Very likely a genuine physical e-paper artifact (incomplete ink-particle clearing/ghosting from the previous image - a known characteristic of multi-color ACeP panels, especially since this screen doesn't do a full clear cycle first) rather than a software bug. Not fixed - would need a real clear-cycle before showing blank, a bigger and riskier hardware-level change than investigated here.

## General polish

- [ ] All fonts, gauge sizes, and region positions in `layout.py` are a first-pass approximation of `weather.css`'s proportions, not pixel-matched to the original design yet.
