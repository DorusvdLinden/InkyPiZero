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
- [ ] `docs/settings.md`'s pollen section says "a real, permanent data-source gap (see `TODO.md`)" (Open-Meteo/CAMS only modeling 6 pollen species vs. Dutch services like pollennieuws.nl grouping mugwort+ragweed+other weeds under a broader "Kruiden" category) but no matching entry exists here - either add one, or drop the cross-reference. Found while working on the RIVM AQI swap (2026-08-14), unrelated to it.
- [ ] **`get_uv_color()` (`weather_data.py`) reads `PALETTE.uv_low/moderate/high/very_high/extreme`, but those are only refreshed by `WeatherCanvas.__init__`'s `PALETTE.set_saturation(config.inky_saturation)` call - and `fetch_snapshot()` (which calls `get_uv_color()` via `_parse_data_points`) always runs *before* `WeatherCanvas` is constructed** (`main.py`: `fetch_snapshot()` at line 52/67, `render_canvas()`/`WeatherCanvas(...)` afterward at line 53/73). So the UV icon color is always resolved at whatever saturation the `PALETTE` singleton was last synced to (the 0.0 module-load default on every one-shot `main.py` run), never the render's actual configured `inky_saturation`, for any user who's changed that setting from the default. Confirmed empirically 2026-08-15 (`get_uv_color(7)` returns saturation-0.0 orange regardless of what saturation is configured) while building the forecast-card weather-quality feature, which had the identical bug pattern - fixed there by passing `config.inky_saturation` through explicitly instead of reading `PALETTE.saturation`; the same fix would apply here (or fixing `_parse_data_points`'s UV block the same way). Not fixed as part of that work - unrelated feature, existing behavior, scope kept narrow.
