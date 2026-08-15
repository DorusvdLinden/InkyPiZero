# pi_weather_display - known issues & ideas

Running list of things found during development/testing that aren't fixed yet.
Add to this whenever something rough turns up; check items off (don't delete
them) once fixed. Grouped by area, open items first in each group. See also
`docs/settings.md`, `docs/icons.md`, and `docs/changes.md` for the broader
reference docs this list feeds into.

## Icons
See Icon-Plan.md


## General polish

- [ ] All fonts, gauge sizes, and region positions in `layout.py` are a first-pass approximation of `weather.css`'s proportions, not pixel-matched to the original design yet.
- [x] `docs/settings.md`'s pollen section said "a real, permanent data-source gap (see `TODO.md`)" (Open-Meteo/CAMS only modeling 6 pollen species vs. Dutch services like pollennieuws.nl grouping mugwort+ragweed+other weeds under a broader "Kruiden" category) but no matching entry existed here. Found while working on the RIVM AQI swap (2026-08-14), unrelated to it. Resolved 2026-08-15: dropped the cross-reference - the gap is already explained inline where it's mentioned, no separate tracked entry needed.
- [x] **`get_uv_color()` (`weather_data.py`) read `PALETTE.uv_low/moderate/high/very_high/extreme`, but those are only refreshed by `WeatherCanvas.__init__`'s `PALETTE.set_saturation(config.inky_saturation)` call - and `fetch_snapshot()` (which calls `get_uv_color()` via `_parse_data_points`) always runs *before* `WeatherCanvas` is constructed**, so the UV icon color was always resolved at whatever saturation `PALETTE` was last synced to (the 0.0 module-load default on every one-shot `main.py` run), never the render's actual configured `inky_saturation`. Found 2026-08-14 while building the forecast-card weather-quality feature (identical bug pattern there). Fixed 2026-08-15: `get_uv_color`/`_parse_data_points` now take `saturation` as an explicit argument (`config.inky_saturation`, threaded through from `fetch_snapshot`) instead of reading the timing-dependent `PALETTE` singleton - `scripts/test_palette_sync.py` gained a regression test for this exact scenario, since its existing tests only checked `PALETTE.saturation` after a `WeatherCanvas`/`render_setup_screen` call and would never have caught a bug in code that runs *before* that sync happens.
