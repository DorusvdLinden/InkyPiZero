"""Deterministic coverage for the multi-day forecast cards' weather-quality
border color and rain-mm text (weather_data._quality_tier_and_color /
_load_weather_quality_config / DayForecast.quality_border_color/
rain_expected/precip_mm) - not part of the app. test_locations.py exercises
real live weather, but live data can't reliably guarantee an exact boundary
value (e.g. a day whose high lands on exactly 26 C) or two inputs
disagreeing in opposite directions (e.g. a cold, heavy-rain day) on any
given test run. This script fakes only the Open-Meteo *forecast* fetch
with a uniform daily high/precipitation across the whole window, then runs
the real fetch_snapshot -> classify -> render pipeline unmodified on top
of it (air quality and location-name lookups still hit the real network).

Also covers weather_quality.toml's fail-soft fallback (missing/unreadable
file falls back to _DEFAULT_WEATHER_QUALITY_CONFIG rather than crashing
the render) - a hand-edited file is exactly the kind of thing that can
break in ways live testing won't reliably catch.

Renders each scenario in all three screen modes and saves to
mock_display_output/forecast_quality_scenario_test/. Run alongside
test_locations.py after any change to weather_data.py's forecast-card
quality scoring, weather_quality.toml, or widgets/forecast.py's card
rendering - see CLAUDE.md.
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
from widgets.palette import PALETTE, native_colors
from display.mock_driver import MockDriver
import display_mode

ICON_DIR = os.path.join(REPO_DIR, "assets", "icons")
FONT_DIR = os.path.join(REPO_DIR, "assets", "fonts")
OUT_DIR = os.path.join(REPO_DIR, "mock_display_output", "forecast_quality_scenario_test")
os.makedirs(OUT_DIR, exist_ok=True)

SCREEN_MODES = sorted(display_mode.VALID_MODES)
HOURS = 48
DAYS = 8  # DisplayConfig.forecast_days(7) + 1

# Resolved dynamically against the running saturation, same as the app
# does, rather than hardcoding RGB tuples that'd drift if the default
# saturation ever changes.
COLORS = native_colors(PALETTE.saturation)


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

# (expected color name, expected rain_expected) - color name looked up in
# COLORS at assertion time so this stays correct at any saturation.
EXPECTED = {
    "pleasant_dry": ("green", False),
    "cold_dry_fair": ("yellow", False),
    "hot_dry_bad": ("orange", False),
    "heavy_rain_mild_temp": ("red", True),
    "boundary_temp_25_good": ("green", False),
    "boundary_temp_26_bad": ("orange", False),
    "boundary_precip_0.2_wet": ("yellow", True),
    "boundary_precip_0.19_dry": ("green", False),
    "extreme_cold": ("red", False),
    "extreme_hot": ("red", False),
    "cold_and_rainy_both_bad": ("red", True),
    "moderate_rain_pleasant_temp": ("orange", True),
}


def _check_one_fallback(name, write_bad_file) -> tuple[str, str]:
    """Points WEATHER_QUALITY_CONFIG_PATH at a file write_bad_file()
    populates (or a nonexistent path, if write_bad_file is None), and
    confirms _load_weather_quality_config() falls back to
    _DEFAULT_WEATHER_QUALITY_CONFIG rather than raising - checked
    directly against the loader (not the full render pipeline) since
    this is about the file, not the classification math covered above."""
    orig_path = weather_data.WEATHER_QUALITY_CONFIG_PATH
    bad_path = os.path.join(REPO_DIR, f"_test_bad_{name}.toml")
    try:
        if write_bad_file is not None:
            write_bad_file(bad_path)
            weather_data.WEATHER_QUALITY_CONFIG_PATH = bad_path
        else:
            weather_data.WEATHER_QUALITY_CONFIG_PATH = os.path.join(REPO_DIR, "_test_does_not_exist.toml")
        config = weather_data._load_weather_quality_config()
        ok = config == weather_data._DEFAULT_WEATHER_QUALITY_CONFIG
    finally:
        weather_data.WEATHER_QUALITY_CONFIG_PATH = orig_path
        if os.path.exists(bad_path):
            os.remove(bad_path)
    status = "OK" if ok else "FAIL: did not fall back to defaults"
    print(f"{'OK' if ok else 'FAIL':6s}{name:28s} (fail-soft fallback)")
    return name, status


def _check_fallback():
    """weather_quality.toml missing/unreadable/invalid must fall back to
    _DEFAULT_WEATHER_QUALITY_CONFIG rather than crash the render - a
    hand-edited file can break in more ways than "doesn't exist", so this
    covers each kind of mistake _load_weather_quality_config/
    _validate_weather_quality_config are meant to catch."""
    def write(text):
        return lambda path: open(path, "w", encoding="utf-8").write(text)

    def write_bad_utf8(path):
        with open(path, "wb") as f:
            f.write(b'[tiers]\nGoed = "green"\n\xff\xfe invalid utf8 bytes')

    cases = {
        "missing_file": None,
        "invalid_color": write('[tiers]\nGoed = "notacolor"\n[[temperature]]\ntier = "Goed"\n[[precipitation]]\ntier = "Goed"\n'),
        "unparseable_toml": write("[tiers\nnot valid toml at all"),
        "bad_utf8": write_bad_utf8,
        # No catch-all last band (every entry has "max") - a value beyond
        # the highest threshold must not silently read as the best tier.
        "no_catchall_band": write('[tiers]\nGoed = "green"\n"Zeer slecht" = "red"\n'
                                   '[[temperature]]\nmax = 30\ntier = "Goed"\n'
                                   '[[precipitation]]\nmax = 15\ntier = "Goed"\n'),
        # Non-numeric "max" - must not crash _band_tier's "<" comparison.
        "non_numeric_max": write('[tiers]\nGoed = "green"\n'
                                  '[[temperature]]\nmax = "cold"\ntier = "Goed"\n[[temperature]]\ntier = "Goed"\n'
                                  '[[precipitation]]\ntier = "Goed"\n'),
        # Doubled brackets ([[tiers]] instead of [tiers]) - a plausible
        # copy-paste mistake right next to [[temperature]]/[[precipitation]]'s
        # genuine array-of-tables syntax. Parses "tiers" as a list, and
        # list.values() must not crash with an uncaught AttributeError.
        "doubled_tiers_brackets": write('[[tiers]]\nGoed = "green"\n'
                                         '[[temperature]]\ntier = "Goed"\n[[precipitation]]\ntier = "Goed"\n'),
    }
    return [_check_one_fallback(name, write_bad_file) for name, write_bad_file in cases.items()]


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
        expected_color_name, expected_rain = EXPECTED[name]
        expected_color = COLORS[expected_color_name]
        ok = day.quality_border_color == expected_color and day.rain_expected == expected_rain
        status = "OK" if ok else (f"FAIL: expected color={expected_color_name} rain_expected={expected_rain}, "
                                   f"got color={day.quality_border_color} rain_expected={day.rain_expected}")
        results.append((name, status))
        print(f"{'OK' if ok else 'FAIL':6s}{name:28s} high={high_c:>5}C precip={precip_mm:>5}mm "
              f"-> color={day.quality_border_color} rain_expected={day.rain_expected} precip_mm={day.precip_mm}")

        for mode in SCREEN_MODES:
            image = WeatherCanvas(assets, config, mode).render(data)
            out_path = os.path.join(OUT_DIR, f"{name}_{mode}.png")
            MockDriver(out_path).show(image)

    results.extend(_check_fallback())

    # A non-default inky_saturation must actually be used for the border
    # color - fetch_snapshot() runs before WeatherCanvas ever calls
    # PALETTE.set_saturation() for this render, so reading the shared
    # PALETTE.saturation instead of config.inky_saturation directly would
    # silently produce the wrong color for anyone who's changed this
    # setting from the default (caught by review, see docs/changes.md).
    saturated_config = DisplayConfig(inky_saturation=0.7)
    payload = _make_payload(28.0, 0.0)  # hot_dry_bad -> orange
    orig_fetch = weather_data._get_open_meteo_data
    weather_data._get_open_meteo_data = lambda *a, **k: payload
    try:
        data = weather_data.fetch_snapshot(saturated_config)
    finally:
        weather_data._get_open_meteo_data = orig_fetch
    expected = native_colors(0.7)["orange"]
    got = data.daily[0].quality_border_color
    ok = got == expected
    status = "OK" if ok else f"FAIL: expected {expected} at saturation=0.7, got {got}"
    results.append(("saturation_threading", status))
    print(f"{'OK' if ok else 'FAIL':6s}{'saturation_threading':28s} expected={expected} got={got}")

    print("\n--- Summary ---")
    for name, status in results:
        print(f"{status:8s} {name}")


if __name__ == "__main__":
    main()
