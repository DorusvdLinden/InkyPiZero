"""Deterministic coverage for the combined "Kwaliteit & Pollen" data point
(weather_data._classify_pollen / _combine_aqi_pollen_tier /
get_combined_rotation) - not part of the app. test_locations.py exercises
real live weather, but live data can't reliably guarantee every combined
tier (or the no-data fallback) on any given test run - Open-Meteo's pollen
coverage is Europe-only and null outside each species' active season, and
a real AQI+pollen combination worth testing (e.g. AQI good but pollen
severe) is even less guaranteed live. This script fakes only the
Open-Meteo *air quality* fetch (the same endpoint pollen shares with
UV/AQI) with crafted hourly pollen and european_aqi values for each
scenario, then runs the real fetch_snapshot -> classify -> render pipeline
unmodified on top of it (the forecast fetch and location-name lookup
still hit the real network).

Renders each scenario in all three screen modes and saves to
mock_display_output/pollen_scenario_test/. Run alongside test_locations.py
and test_precip_scenarios.py after any change to weather_data.py's pollen/
AQI classification or to canvas.py's/layout.py's compact-grid code - see
CLAUDE.md.
"""

import os
import sys
from datetime import datetime, timedelta

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)
os.chdir(REPO_DIR)

import weather_data
from config import DisplayConfig
from canvas import WeatherCanvas, _data_point_value_text
from widgets.icons import AssetStore
from display.mock_driver import MockDriver
import display_mode

ICON_DIR = os.path.join(REPO_DIR, "assets", "icons")
FONT_DIR = os.path.join(REPO_DIR, "assets", "fonts")
OUT_DIR = os.path.join(REPO_DIR, "mock_display_output", "pollen_scenario_test")
os.makedirs(OUT_DIR, exist_ok=True)

SCREEN_MODES = sorted(display_mode.VALID_MODES)
HOURS = 48


def _make_payload(pollen_values: dict, aqi_value: float | None = None) -> dict:
    """pollen_values maps a subset of weather_data.POLLEN_SPECIES_NL's keys
    to a constant grains/m3 value held across the whole window; species not
    included stay null (as Open-Meteo returns outside their season).
    aqi_value, if given, is held constant across the whole window too;
    None leaves european_aqi null (as if AQI data were unavailable)."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    hourly_times = [(now + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(HOURS)]
    hourly = {"time": hourly_times}
    for species in weather_data.POLLEN_SPECIES_NL:
        value = pollen_values.get(species)
        hourly[species] = [value] * HOURS if value is not None else [None] * HOURS
    hourly["european_aqi"] = [aqi_value] * HOURS if aqi_value is not None else [None] * HOURS
    return {"hourly": hourly}


def _make_daily_peak_dip_payload() -> dict:
    """Regression for classifying by today's peak rather than the exact
    current hour (weather_data._value_max_today): grass_pollen dips at the
    current hour but peaks later today - classification must pick up the
    peak. (Assumes at least one hour is left today when this test runs -
    same real-time-dependent caveat as this script's other scenarios.)"""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    today = now.date()
    hourly_times = [(now + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(HOURS)]
    grass = []
    for i in range(HOURS):
        hour_date = (now + timedelta(hours=i)).date()
        if i == 0:
            grass.append(2.0)  # dip at the exact current hour
        elif hour_date == today:
            grass.append(9.0)  # peak later today
        else:
            grass.append(2.0)
    hourly = {"time": hourly_times, "grass_pollen": grass, "european_aqi": [None] * HOURS}
    for species in weather_data.POLLEN_SPECIES_NL:
        if species != "grass_pollen":
            hourly[species] = [None] * HOURS
    return {"hourly": hourly}


SCENARIOS = {
    "no_data": lambda: _make_payload({}),
    # pure-pollen scenarios (AQI unavailable) - combined tier/species should
    # follow pollen's own tier_index 1:1 (see COMBINED_TIERS)
    "pollen_laag": lambda: _make_payload({"grass_pollen": 3}),
    "pollen_matig": lambda: _make_payload({"birch_pollen": 50}),
    "pollen_hoog": lambda: _make_payload({"ragweed_pollen": 40}),
    "pollen_zeer_hoog": lambda: _make_payload({"birch_pollen": 2000}),
    # tie-break: worst tier across species should win, not the first one seen
    "mixed_worst_wins": lambda: _make_payload({"grass_pollen": 3, "birch_pollen": 2000}),
    # regression for a real bug: Open-Meteo reports an off-season species as
    # a flat 0.0 (not null), and it's first in POLLEN_SPECIES_NL's dict
    # order - a same-tier tie must not let that 0.0 species win over a
    # genuinely active one just by iteration order.
    "zero_species_tie": lambda: _make_payload({"alder_pollen": 0.0, "grass_pollen": 4.9}),
    # regression for a real bug: classifying off the exact current hour
    # missed a day that peaked well above the current dip (confirmed
    # against pollennieuws.nl).
    "daily_peak_not_current_hour": _make_daily_peak_dip_payload,
    # combining: AQI alone, pollen unavailable
    "aqi_only": lambda: _make_payload({}, aqi_value=50),  # tier 2 (Matig) -> combined 1
    # combining: AQI is the worse of the two - no species should be named
    "aqi_worse_than_pollen": lambda: _make_payload({"grass_pollen": 3}, aqi_value=90),  # AQI tier 4 -> combined 3
    # combining: pollen is the worse of the two - species should be named
    "pollen_worse_than_aqi": lambda: _make_payload({"birch_pollen": 2000}, aqi_value=10),  # AQI tier 0 -> combined 0
    # combining: tied at "Goed" (pollen is Laag) - category dropped even
    # though pollen_tier_index >= aqi_combined, since Laag isn't worth
    # naming a cause for.
    "tied_tier_pollen_laag": lambda: _make_payload({"grass_pollen": 3}, aqi_value=30),  # AQI tier 1 -> combined 0
    # combining: tied at "Matig" (pollen is genuinely elevated) - category
    # still shown, unlike the Laag tie above.
    "tied_tier_pollen_elevated": lambda: _make_payload({"grass_pollen": 15}, aqi_value=45),  # AQI tier 2 -> combined 1
}

# (expected combined measurement, expected unit/species) or None for the
# neither-available fallback
EXPECTED = {
    "no_data": ("N/A", ""),
    # Laag pollen never names a category, even standing alone (see
    # get_combined_rotation/the label-formatting rule: "Tier: Categorie"
    # only when the category is genuinely elevated).
    "pollen_laag": ("Goed", ""),
    "pollen_matig": ("Matig", "Boom"),
    "pollen_hoog": ("Slecht", "Ambrosia"),
    "pollen_zeer_hoog": ("Zeer slecht", "Boom"),
    "mixed_worst_wins": ("Zeer slecht", "Boom"),
    "zero_species_tie": ("Goed", ""),
    "daily_peak_not_current_hour": ("Matig", "Gras"),
    "aqi_only": ("Matig", ""),
    "aqi_worse_than_pollen": ("Zeer slecht", ""),
    "pollen_worse_than_aqi": ("Zeer slecht", "Boom"),
    "tied_tier_pollen_laag": ("Goed", ""),
    "tied_tier_pollen_elevated": ("Matig", "Gras"),
}


def main():
    assets = AssetStore(ICON_DIR, FONT_DIR)
    config = DisplayConfig()
    results = []

    for name, make_payload in SCENARIOS.items():
        payload = make_payload()
        orig_fetch = weather_data._get_open_meteo_air_quality
        weather_data._get_open_meteo_air_quality = lambda *a, **k: payload
        try:
            data = weather_data.fetch_snapshot(config)
        finally:
            weather_data._get_open_meteo_air_quality = orig_fetch

        aqi_points = [dp for dp in data.data_points if dp["kind"] == "aqi"]
        has_visibility = any(dp["kind"] == "visibility" for dp in data.data_points)
        expected = EXPECTED[name]
        expected_text = f"{expected[0]}: {expected[1]}" if expected[1] else expected[0]
        got = (aqi_points[0]["measurement"], aqi_points[0]["unit"]) if aqi_points else "no aqi point"
        got_text = _data_point_value_text(aqi_points[0]) if aqi_points else "no aqi point"
        ok = len(aqi_points) == 1 and got == expected and got_text == expected_text and has_visibility
        status = "OK" if ok else (f"FAIL: expected {expected!r}/{expected_text!r} (+visibility), "
                                   f"got {got!r}/{got_text!r} (visibility={has_visibility})")
        results.append((name, status))
        print(f"{'OK' if ok else 'FAIL':6s}{name:22s} {got!r}")

        for mode in SCREEN_MODES:
            image = WeatherCanvas(assets, config, mode).render(data)
            out_path = os.path.join(OUT_DIR, f"{name}_{mode}.png")
            MockDriver(out_path).show(image)

    print("\n--- Summary ---")
    for name, status in results:
        print(f"{status:8s} {name}")


if __name__ == "__main__":
    main()
