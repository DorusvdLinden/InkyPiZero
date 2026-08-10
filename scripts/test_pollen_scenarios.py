"""Deterministic coverage for the pollen/hay-fever data point
(weather_data._classify_pollen / get_pollen_color) - not part of the app.
test_locations.py exercises real live weather, but live data can't
reliably guarantee every tier (or the no-data fallback) on any given test
run - Open-Meteo's pollen coverage is Europe-only and null outside each
species' active season. This script fakes only the Open-Meteo *air
quality* fetch (the same endpoint pollen shares with UV/AQI) with crafted
hourly pollen values for each scenario, then runs the real fetch_snapshot
-> classify -> render pipeline unmodified on top of it (the forecast fetch
and location-name lookup still hit the real network).

Renders each scenario in all three screen modes and saves to
mock_display_output/pollen_scenario_test/. Run alongside test_locations.py
and test_precip_scenarios.py after any change to weather_data.py's pollen
classification or to canvas.py's/layout.py's compact-grid code - see
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
from canvas import WeatherCanvas
from widgets.icons import AssetStore
from display.mock_driver import MockDriver
import display_mode

ICON_DIR = os.path.join(REPO_DIR, "assets", "icons")
FONT_DIR = os.path.join(REPO_DIR, "assets", "fonts")
OUT_DIR = os.path.join(REPO_DIR, "mock_display_output", "pollen_scenario_test")
os.makedirs(OUT_DIR, exist_ok=True)

SCREEN_MODES = sorted(display_mode.VALID_MODES)
HOURS = 48


def _make_payload(pollen_values: dict) -> dict:
    """pollen_values maps a subset of weather_data.POLLEN_SPECIES_NL's keys
    to a constant grains/m3 value held across the whole window; species not
    included stay null (as Open-Meteo returns outside their season)."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    hourly_times = [(now + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(HOURS)]
    hourly = {"time": hourly_times}
    for species in weather_data.POLLEN_SPECIES_NL:
        value = pollen_values.get(species)
        hourly[species] = [value] * HOURS if value is not None else [None] * HOURS
    return {"hourly": hourly}


SCENARIOS = {
    "no_data": lambda: _make_payload({}),
    "laag": lambda: _make_payload({"grass_pollen": 3}),
    "matig": lambda: _make_payload({"birch_pollen": 50}),
    "hoog": lambda: _make_payload({"ragweed_pollen": 40}),
    "zeer_hoog": lambda: _make_payload({"birch_pollen": 2000}),
    # tie-break: worst tier across species should win, not the first one seen
    "mixed_worst_wins": lambda: _make_payload({"grass_pollen": 3, "birch_pollen": 2000}),
}

EXPECTED = {
    "no_data": None,
    "laag": ("Laag", "Gras"),
    "matig": ("Matig", "Berk"),
    "hoog": ("Hoog", "Ambrosia"),
    "zeer_hoog": ("Zeer hoog", "Berk"),
    "mixed_worst_wins": ("Zeer hoog", "Berk"),
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

        pollen_points = [dp for dp in data.data_points if dp["kind"] == "pollen"]
        expected = EXPECTED[name]
        if expected is None:
            ok = len(pollen_points) == 0 and any(dp["kind"] == "visibility" for dp in data.data_points)
            got = "no pollen point, visibility present" if ok else [dp["kind"] for dp in data.data_points]
        else:
            ok = len(pollen_points) == 1 and (pollen_points[0]["measurement"], pollen_points[0]["unit"]) == expected
            got = (pollen_points[0]["measurement"], pollen_points[0]["unit"]) if pollen_points else "no pollen point"
        status = "OK" if ok else f"FAIL: expected {expected!r}, got {got!r}"
        results.append((name, status))
        print(f"{'OK' if ok else 'FAIL':6s}{name:18s} {got!r}")

        for mode in SCREEN_MODES:
            image = WeatherCanvas(assets, config, mode).render(data)
            out_path = os.path.join(OUT_DIR, f"{name}_{mode}.png")
            MockDriver(out_path).show(image)

    print("\n--- Summary ---")
    for name, status in results:
        print(f"{status:8s} {name}")


if __name__ == "__main__":
    main()
