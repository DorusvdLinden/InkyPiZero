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

## Fonts & text

- [x] **Bitter adopted as the default font (2026-08-11)**: after the earlier "all three rejected, keep Jost" conclusion, a further round pushed several more real-hardware comparisons (Literata, Charter, Bitter, Vollkorn, plus a local-only Georgia digital check - Bookerly couldn't be sourced at all, proprietary to Kindle) - Bitter won. `config.font_family` (`"jost"` | `"bitter"`, see `widgets/icons.py`'s `FONT_FAMILIES`) is now a real web UI setting, default `"bitter"`. Bitter ships as a single variable-weight file - `AssetStore.font()` selects its named Bold/Regular instance via `set_variation_by_name()`. Testing across the *full* app (not just isolated samples) found and fixed a real bug: Bitter is wider than Jost at the same point size, which clipped the "Kwaliteit & Pollen" label in the 6-cell (original/gridlines) data-point grid - `_draw_data_points` now uses the same `_fit_font` width-shrinking `_draw_compact_cell` already had.
- [ ] **Chart gridline-mode max-value label can collide with the topmost tick label** - found (again) while testing Bitter on Ulaanbaatar's data, but confirmed with a same-data side-by-side render that it reproduces identically with Jost too, so it's font-independent, not new. Matches an earlier finding from imperial-unit testing (since removed along with imperial/standard support) that predicted this could also happen "in metric on the right data" - it can. No minimum-gap check between the axis-extreme label and the nearest gridline tick label in `widgets/chart.py`. Not fixed.
- [ ] **Missing font glyph fallback**: `AssetStore.font()` only loads Latin-script fonts (Jost or Bitter, no CJK/other non-Latin glyphs). When a location name comes back in a non-Latin script (e.g. Tokyo's Nominatim result), PIL silently drops the unsupported characters instead of rendering anything - the header ends up with a blank gap where the city name should be. The old Chromium/CSS renderer didn't hit this because browsers do automatic per-character font fallback; Pillow's single-TTF loader doesn't. Found via `mock_display_output/pi_zero/pi_zero_render_tokyo_japan.png`. Fix likely needs a bundled fallback font (broad Unicode coverage) tried per-character when the active font can't render something.

## WiFi & web UI

- [ ] **No SSID rename**: `wifi_manager.edit_network()` can only update a saved network's password/priority - the con-name and SSID are set together at creation, so a changed SSID needs remove + re-add rather than an in-place rename. Documented in the `/wifi` page copy and `docs/networking.md`, not fixed.
- [ ] **No periodic reconnect check**: `web_app.py`'s connectivity check (activate the setup AP if nothing's reachable) only runs once, at `pi-weather-web.service` startup - if a previously-good station connection drops later at runtime (router reboot, moved out of range), the device stays disconnected until the service is manually restarted rather than automatically falling back to the setup AP. Deliberately out of v1 scope - see the plan's Phase 8.
- [ ] **No real captive-portal DNS redirect** on the setup AP - joining it and opening any URL doesn't auto-redirect to the setup page like commercial IoT devices do; the user has to know/read the exact URL (`http://192.168.4.1`) shown on the e-paper display and type it manually. `dnsmasq-base` (already a dependency) could serve wildcard DNS for this later.
- [ ] **No authentication anywhere in the web UI** - settings edits, WiFi credential changes, and shutdown are all reachable by anyone who can reach the device's IP or join its setup AP. Deliberate, matches button A's existing unauthenticated physical shutdown and the project's trusted-LAN-only threat model - documented explicitly in `docs/networking.md`, not an oversight, but would need revisiting if this device is ever exposed beyond a home LAN.
- [ ] No QR code on the setup screen (would encode `WIFI:S:<ssid>;T:WPA;P:<password>;;` for one-tap phone connect) - would need a new `qrcode` dependency and more rendering work, scoped out of v1.



## General polish

- [ ] All fonts, gauge sizes, and region positions in `layout.py` are a first-pass approximation of `weather.css`'s proportions, not pixel-matched to the original design yet.
