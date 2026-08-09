"""Deterministic coverage for the chart's precipitation axis label
(weather_data._classify_precip / WeatherSnapshot.precip_label) - not part of
the app. test_locations.py exercises real live weather, but live data can't
reliably guarantee all four label branches on any given test run (a hailstorm
in particular). This script fakes only the Open-Meteo *forecast* fetch with
crafted weather-code/precipitation/snowfall data for each branch, then runs
the real fetch_snapshot -> classify -> render pipeline unmodified on top of
it (air quality and location-name lookups still hit the real network).

Renders each scenario in all three screen modes and saves to
mock_display_output/precip_scenario_test/. Run alongside test_locations.py
after any change to weather_data.py's precipitation classification or to
widgets/chart.py's axis-label rendering - see CLAUDE.md.
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
OUT_DIR = os.path.join(REPO_DIR, "mock_display_output", "precip_scenario_test")
os.makedirs(OUT_DIR, exist_ok=True)

SCREEN_MODES = sorted(display_mode.VALID_MODES)
HOURS = 48
DAYS = 8  # DisplayConfig.forecast_days(7) + 1


def _make_payload(hourly_code, hourly_precip, hourly_snow):
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    hourly_times = [(now + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(HOURS)]
    temps = [15.0 + (5 if 8 <= (now + timedelta(hours=i)).hour <= 18 else 0) for i in range(HOURS)]

    day0 = now.date()
    daily_times = [(day0 + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(DAYS)]
    sunrise = [(day0 + timedelta(days=i)).strftime("%Y-%m-%dT07:00") for i in range(DAYS)]
    sunset = [(day0 + timedelta(days=i)).strftime("%Y-%m-%dT21:00") for i in range(DAYS)]

    return {
        "timezone": "Europe/Amsterdam",
        "current": {
            "time": hourly_times[0],
            "temperature": temps[0],
            "windspeed": 3.2,
            "winddirection": 220,
            "is_day": 1,
            "precipitation": hourly_precip[0],
            "weather_code": hourly_code[0],
            "apparent_temperature": temps[0] - 1,
        },
        "daily": {
            "time": daily_times,
            "weathercode": [hourly_code[(i * 24) % HOURS] for i in range(DAYS)],
            "temperature_2m_max": [max(temps) for _ in range(DAYS)],
            "temperature_2m_min": [min(temps) for _ in range(DAYS)],
            "sunrise": sunrise,
            "sunset": sunset,
        },
        "hourly": {
            "time": hourly_times,
            "temperature_2m": temps,
            "precipitation": hourly_precip,
            "precipitation_probability": [80] * HOURS,
            "relative_humidity_2m": [70] * HOURS,
            "surface_pressure": [1013] * HOURS,
            "visibility": [15000] * HOURS,
            "snowfall": hourly_snow,
            "weather_code": hourly_code,
        },
    }


SCENARIOS = {
    # steady moderate rain (WMO 63) across the whole window
    "rain": lambda: _make_payload([63] * HOURS, [2.4] * HOURS, [0.0] * HOURS),
    # a thunderstorm-with-hail hour (WMO 96) mixed into an otherwise rainy window
    "hail": lambda: _make_payload(
        [61, 61, 96, 63, 61] + [61] * (HOURS - 5),
        [1.0, 1.0, 3.5, 2.0, 1.0] + [1.0] * (HOURS - 5),
        [0.0] * HOURS,
    ),
    # steady snow (WMO 73)
    "snow": lambda: _make_payload([73] * HOURS, [0.0] * HOURS, [1.2] * HOURS),
    # clear, nothing falling at all
    "dry": lambda: _make_payload([0] * HOURS, [0.0] * HOURS, [0.0] * HOURS),
}

EXPECTED_LABEL_PREFIX = {"rain": "Regen", "hail": "Hagel", "snow": "Sneeuw", "dry": "Droog"}


def main():
    assets = AssetStore(ICON_DIR, FONT_DIR)
    config = DisplayConfig()
    results = []

    for name, make_payload in SCENARIOS.items():
        payload = make_payload()
        orig_fetch = weather_data._get_open_meteo_data
        weather_data._get_open_meteo_data = lambda *a, **k: payload
        try:
            data = weather_data.fetch_snapshot(config)
        finally:
            weather_data._get_open_meteo_data = orig_fetch

        ok = data.precip_label.startswith(EXPECTED_LABEL_PREFIX[name])
        status = "OK" if ok else f"FAIL: expected {EXPECTED_LABEL_PREFIX[name]!r}, got {data.precip_label!r}"
        results.append((name, status))
        print(f"{'OK' if ok else 'FAIL':6s}{name:6s} precip_label={data.precip_label!r}")

        for mode in SCREEN_MODES:
            image = WeatherCanvas(assets, config, mode).render(data)
            out_path = os.path.join(OUT_DIR, f"{name}_{mode}.png")
            MockDriver(out_path).show(image)

    print("\n--- Summary ---")
    for name, status in results:
        print(f"{status:8s} {name}")


if __name__ == "__main__":
    main()
