"""Deterministic coverage for the multi-day forecast cards' quality-tier
border color and rain-mm text (weather_data._temp_quality_tier /
_precip_quality_tier / DayForecast.quality_tier_index/rain_expected/
precip_mm) - not part of the app. test_locations.py exercises real live
weather, but live data can't reliably guarantee an exact boundary value
(e.g. a day whose high lands on exactly 26 C) or two inputs disagreeing
in opposite directions (e.g. a cold, heavy-rain day) on any given test
run. This script fakes only the Open-Meteo *forecast* fetch with a
uniform daily high/precipitation across the whole window, then runs the
real fetch_snapshot -> classify -> render pipeline unmodified on top of
it (air quality and location-name lookups still hit the real network).

Renders each scenario in all three screen modes and saves to
mock_display_output/forecast_quality_scenario_test/. Run alongside
test_locations.py after any change to weather_data.py's forecast-card
quality scoring or to widgets/forecast.py's card rendering - see
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
OUT_DIR = os.path.join(REPO_DIR, "mock_display_output", "forecast_quality_scenario_test")
os.makedirs(OUT_DIR, exist_ok=True)

SCREEN_MODES = sorted(display_mode.VALID_MODES)
HOURS = 48
DAYS = 8  # DisplayConfig.forecast_days(7) + 1


def _make_payload(high_c: float, precip_mm: float) -> dict:
    """Every day in the window gets the same high/precipitation, so the
    whole forecast row exercises one scenario uniformly - mirrors
    test_precip_scenarios.py's style. weathercode is a plain "clear"
    (WMO 0) regardless of precip_mm - the card's quality tier and mm-text
    are driven by precipitation_sum/temperature_2m_max, not by weathercode,
    so this deliberately doesn't need to pick a precip-coded weathercode
    to exercise rain scenarios."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    hourly_times = [(now + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(HOURS)]
    temps = [high_c] * HOURS

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
            "temperature_2m": temps,
            "precipitation": [0.0] * HOURS,
            "precipitation_probability": [0] * HOURS,
            "relative_humidity_2m": [70] * HOURS,
            "surface_pressure": [1013] * HOURS,
            "visibility": [15000] * HOURS,
            "snowfall": [0.0] * HOURS,
            "weather_code": [0] * HOURS,
        },
    }


# (high_c, precip_mm) per scenario - covers every tier, both boundary
# edges (temp 25/26, precip 0.19/0.2), the two extremes on both hot and
# cold sides, and the inputs disagreeing in opposite directions.
SCENARIOS = {
    "pleasant_dry": (20.0, 0.0),
    "cold_dry_fair": (5.0, 0.0),
    "hot_dry_bad": (28.0, 0.0),
    "heavy_rain_mild_temp": (20.0, 20.0),
    "boundary_temp_25_good": (25.0, 0.0),
    "boundary_temp_26_bad": (26.0, 0.0),
    "boundary_precip_0.2_wet": (20.0, 0.2),
    "boundary_precip_0.19_dry": (20.0, 0.19),
    "extreme_cold": (-10.0, 0.0),
    "extreme_hot": (35.0, 0.0),
    "cold_and_rainy_both_bad": (-2.0, 20.0),
    "moderate_rain_pleasant_temp": (20.0, 8.0),
}

# (expected quality_tier_index, expected rain_expected)
EXPECTED = {
    "pleasant_dry": (0, False),
    "cold_dry_fair": (1, False),
    "hot_dry_bad": (2, False),
    "heavy_rain_mild_temp": (3, True),
    "boundary_temp_25_good": (0, False),
    "boundary_temp_26_bad": (2, False),
    "boundary_precip_0.2_wet": (1, True),
    "boundary_precip_0.19_dry": (0, False),
    "extreme_cold": (3, False),
    "extreme_hot": (3, False),
    "cold_and_rainy_both_bad": (3, True),
    "moderate_rain_pleasant_temp": (2, True),
}


def main():
    assets = AssetStore(ICON_DIR, FONT_DIR)
    config = DisplayConfig()
    results = []

    for name, (high_c, precip_mm) in SCENARIOS.items():
        payload = _make_payload(high_c, precip_mm)
        orig_fetch = weather_data._get_open_meteo_data
        weather_data._get_open_meteo_data = lambda *a, **k: payload
        try:
            data = weather_data.fetch_snapshot(config)
        finally:
            weather_data._get_open_meteo_data = orig_fetch

        day = data.daily[0]
        expected_tier, expected_rain = EXPECTED[name]
        got = (day.quality_tier_index, day.rain_expected)
        ok = got == (expected_tier, expected_rain)
        tier_name = weather_data.FORECAST_QUALITY_TIERS[day.quality_tier_index]
        status = "OK" if ok else (f"FAIL: expected tier={expected_tier} "
                                   f"({weather_data.FORECAST_QUALITY_TIERS[expected_tier]}) "
                                   f"rain_expected={expected_rain}, got tier={day.quality_tier_index} "
                                   f"({tier_name}) rain_expected={day.rain_expected}")
        results.append((name, status))
        print(f"{'OK' if ok else 'FAIL':6s}{name:28s} high={high_c:>5}C precip={precip_mm:>5}mm "
              f"-> {tier_name:11s} rain_expected={day.rain_expected} precip_mm={day.precip_mm}")

        for mode in SCREEN_MODES:
            image = WeatherCanvas(assets, config, mode).render(data)
            out_path = os.path.join(OUT_DIR, f"{name}_{mode}.png")
            MockDriver(out_path).show(image)

    print("\n--- Summary ---")
    for name, status in results:
        print(f"{status:8s} {name}")


if __name__ == "__main__":
    main()
