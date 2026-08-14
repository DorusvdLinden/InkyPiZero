"""Deterministic coverage for the multi-day forecast cards' rain-mm text
(weather_data.FORECAST_DRY_MM_THRESHOLD / DayForecast.rain_expected/
precip_mm) - not part of the app. test_locations.py exercises real live
weather, but live data can't reliably guarantee an exact boundary value
(a day whose precipitation_sum lands on exactly the 0.2mm dry/wet cutoff)
on any given test run. This script fakes only the Open-Meteo *forecast*
fetch with a uniform daily precipitation across the whole window, then
runs the real fetch_snapshot -> classify -> render pipeline unmodified on
top of it (air quality and location-name lookups still hit the real
network).

Renders each scenario in all three screen modes and saves to
mock_display_output/forecast_rain_scenario_test/. Run alongside
test_locations.py after any change to weather_data.py's forecast-card
precipitation handling or to widgets/forecast.py's card rendering - see
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
OUT_DIR = os.path.join(REPO_DIR, "mock_display_output", "forecast_rain_scenario_test")
os.makedirs(OUT_DIR, exist_ok=True)

SCREEN_MODES = sorted(display_mode.VALID_MODES)
HOURS = 48
DAYS = 8  # DisplayConfig.forecast_days(7) + 1


def _make_payload(precip_mm: float) -> dict:
    """Every day in the window gets the same precipitation, so the whole
    forecast row exercises one scenario uniformly - mirrors
    test_precip_scenarios.py's style. weathercode is a plain "clear"
    (WMO 0) regardless of precip_mm - the mm-text is driven by
    precipitation_sum, not by weathercode, so this deliberately doesn't
    need a precip-coded weathercode to exercise rain scenarios."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    hourly_times = [(now + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(HOURS)]
    high_c = 18.0

    day0 = now.date()
    daily_times = [(day0 + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(DAYS)]
    sunrise = [(day0 + timedelta(days=i)).strftime("%Y-%m-%dT07:00") for i in range(DAYS)]
    sunset = [(day0 + timedelta(days=i)).strftime("%Y-%m-%dT21:00") for i in range(DAYS)]

    return {
        "timezone": "Europe/Amsterdam",
        "current": {
            "time": hourly_times[0],
            "temperature": high_c,
            "windspeed": 3.2,
            "winddirection": 220,
            "is_day": 1,
            "precipitation": 0.0,
            "weather_code": 0,
            "apparent_temperature": high_c - 1,
        },
        "daily": {
            "time": daily_times,
            "weathercode": [0] * DAYS,
            "temperature_2m_max": [high_c] * DAYS,
            "temperature_2m_min": [high_c - 5] * DAYS,
            "precipitation_sum": [precip_mm] * DAYS,
            "sunrise": sunrise,
            "sunset": sunset,
        },
        "hourly": {
            "time": hourly_times,
            "temperature_2m": [high_c] * HOURS,
            "precipitation": [0.0] * HOURS,
            "precipitation_probability": [0] * HOURS,
            "relative_humidity_2m": [70] * HOURS,
            "surface_pressure": [1013] * HOURS,
            "visibility": [15000] * HOURS,
            "snowfall": [0.0] * HOURS,
            "weather_code": [0] * HOURS,
        },
    }


# precip_mm per scenario - covers dry, both sides of the 0.2mm boundary
# exactly, sub-1mm decimal formatting, and a 2-digit whole-mm amount.
SCENARIOS = {
    "dry": 0.0,
    "boundary_0.19_dry": 0.19,
    "boundary_0.2_wet": 0.2,
    "sub_1mm_decimal": 0.6,
    "whole_mm": 4.0,
    "heavy_rain_2digit": 20.0,
}

# (expected rain_expected, expected mm text or None)
EXPECTED = {
    "dry": (False, None),
    "boundary_0.19_dry": (False, None),
    "boundary_0.2_wet": (True, "0.2mm"),
    "sub_1mm_decimal": (True, "0.6mm"),
    "whole_mm": (True, "4mm"),
    "heavy_rain_2digit": (True, "20mm"),
}


def main():
    assets = AssetStore(ICON_DIR, FONT_DIR)
    config = DisplayConfig()
    results = []

    for name, precip_mm in SCENARIOS.items():
        payload = _make_payload(precip_mm)
        orig_fetch = weather_data._get_open_meteo_data
        weather_data._get_open_meteo_data = lambda *a, **k: payload
        try:
            data = weather_data.fetch_snapshot(config)
        finally:
            weather_data._get_open_meteo_data = orig_fetch

        day = data.daily[0]
        expected_rain, expected_text = EXPECTED[name]
        got_text = (f"{day.precip_mm:.1f}mm" if day.precip_mm < 1 else f"{round(day.precip_mm)}mm") if day.rain_expected else None
        ok = day.rain_expected == expected_rain and got_text == expected_text
        status = "OK" if ok else (f"FAIL: expected rain_expected={expected_rain} text={expected_text!r}, "
                                   f"got rain_expected={day.rain_expected} text={got_text!r}")
        results.append((name, status))
        print(f"{'OK' if ok else 'FAIL':6s}{name:22s} precip_mm={precip_mm:>5} "
              f"-> rain_expected={day.rain_expected} text={got_text!r}")

        for mode in SCREEN_MODES:
            image = WeatherCanvas(assets, config, mode).render(data)
            out_path = os.path.join(OUT_DIR, f"{name}_{mode}.png")
            MockDriver(out_path).show(image)

    print("\n--- Summary ---")
    for name, status in results:
        print(f"{status:8s} {name}")


if __name__ == "__main__":
    main()
