"""Consistency test across diverse locations/weather/times - not part of the
app. Fetches each location once via the real fetch->render pipeline, then
renders it in all three screen modes (original/gridlines/compact) and saves
each to mock_display_output/location_consistency_test/ with a descriptive
name, catching (not silencing) any exception per-location so one bad
location doesn't stop the rest.

Run after any change to the rendering pipeline (widgets/, canvas.py,
layout.py, weather_data.py) to check for regressions - see CLAUDE.md. See
also test_precip_scenarios.py, which covers the precipitation-label
rain/hail/snow/dry cases that live weather can't reliably guarantee.
"""

import os
import sys
import traceback

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)
os.chdir(REPO_DIR)

from config import DisplayConfig
from weather_data import fetch_snapshot
from canvas import WeatherCanvas
from widgets.icons import AssetStore
from display.mock_driver import MockDriver
import display_mode

ICON_DIR = os.path.join(REPO_DIR, "assets", "icons")
FONT_DIR = os.path.join(REPO_DIR, "assets", "fonts")

# name, lat, lon, timezone, units, notes
LOCATIONS = [
    ("sittard_netherlands", 51.0004365, 5.8993687, "Europe/Amsterdam", "metric", "baseline, temperate, daytime"),
    ("phoenix_arizona_usa", 33.4484, -112.0740, "America/Phoenix", "metric", "hot desert, daytime"),
    ("dubai_uae", 25.2048, 55.2708, "Asia/Dubai", "metric", "extreme desert heat, evening"),
    ("reykjavik_iceland", 64.1466, -21.9426, "Atlantic/Reykjavik", "metric", "cold, wind/rain, daytime"),
    ("bangkok_thailand", 13.7563, 100.5018, "Asia/Bangkok", "metric", "tropical monsoon rain, night"),
    ("mumbai_india", 19.0760, 72.8777, "Asia/Kolkata", "metric", "monsoon heavy rain, evening"),
    ("sydney_australia", -33.8688, 151.2093, "Australia/Sydney", "metric", "S.hemisphere winter, cold, night"),
    ("ushuaia_argentina", -54.8019, -68.3030, "America/Argentina/Ushuaia", "metric", "far south winter, freezing/snow, daytime"),
    ("tokyo_japan", 35.6762, 139.6503, "Asia/Tokyo", "metric", "humid, possible rain, night"),
    ("sanfrancisco_usa", 37.7749, -122.4194, "America/Los_Angeles", "metric", "mild, fog, early morning"),
    ("auckland_newzealand", -36.8485, 174.7633, "Pacific/Auckland", "metric", "S.hemisphere winter, deep night"),
    ("ulaanbaatar_mongolia", 47.8864, 106.9057, "Asia/Ulaanbaatar", "metric", "continental extreme, night"),
    ("mcmurdo_antarctica", -77.8419, 166.6863, "Antarctica/McMurdo", "metric", "all-negative hourly temps, deep winter"),
    ("bariloche_argentina", -41.1335, -71.3103, "America/Argentina/Buenos_Aires", "metric", "hourly temps cross zero (both + and -)"),
]

SCREEN_MODES = sorted(display_mode.VALID_MODES)

OUT_DIR = os.path.join(REPO_DIR, "mock_display_output", "location_consistency_test")
os.makedirs(OUT_DIR, exist_ok=True)

assets = AssetStore(ICON_DIR, FONT_DIR)

results = []
for name, lat, lon, tz, units, notes in LOCATIONS:
    config = DisplayConfig(latitude=lat, longitude=lon, timezone=tz, units=units)
    try:
        data = fetch_snapshot(config)
        for mode in SCREEN_MODES:
            image = WeatherCanvas(assets, config, mode).render(data)
            out_path = os.path.join(OUT_DIR, f"{name}_{mode}.png")
            MockDriver(out_path).show(image)
        results.append((name, "OK", notes))
        print(f"OK    {name:28s} {notes}")
    except Exception as e:
        results.append((name, f"FAIL: {e}", notes))
        print(f"FAIL  {name:28s} {notes}\n      {e}")
        traceback.print_exc()

print("\n--- Summary ---")
for name, status, notes in results:
    print(f"{status:8s} {name:28s} {notes}")
