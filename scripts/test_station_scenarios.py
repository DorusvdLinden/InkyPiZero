"""Deterministic coverage for weather_data's local weather-station seam
(StationConditions, STATION_ADAPTERS, _get_station_conditions,
_apply_station_rain_override) - not part of the app. No real station
vendor is wired up yet (IDEAS.md), so this monkeypatches the
"generic_http" placeholder adapter directly, plus (for the icon-override
scenarios specifically) the Open-Meteo forecast fetch itself - same crafted-
fixture approach as test_precip_scenarios.py - so the model's "dry" state
is controlled rather than depending on live weather on any given run.

Renders each scenario in all three screen modes and saves to
mock_display_output/station_scenario_test/. Run after any change to
weather_data.py's station seam, canvas.py's current-conditions icon
selection, or config.py/settings_store.py's station_* fields - see
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
OUT_DIR = os.path.join(REPO_DIR, "mock_display_output", "station_scenario_test")
os.makedirs(OUT_DIR, exist_ok=True)

SCREEN_MODES = sorted(display_mode.VALID_MODES)
HOURS = 48
DAYS = 8  # DisplayConfig.forecast_days(7) + 1

DISABLED_CONFIG = DisplayConfig()  # station_enabled=False is the dataclass default
ENABLED_CONFIG = DisplayConfig(station_enabled=True, station_type="generic_http", station_base_url="http://fake-station.local/")


def _make_payload(current_weather_code):
    """A minimal but complete Open-Meteo-shaped payload (same fields
    _merge_model_blend's output has) with a controlled `current.weather_code`
    - everything else is flat/dry so only the station override, not the
    model's own classification, can introduce precipitation."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    hourly_times = [(now + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(HOURS)]
    day0 = now.date()
    daily_times = [(day0 + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(DAYS)]
    sunrise = [(day0 + timedelta(days=i)).strftime("%Y-%m-%dT07:00") for i in range(DAYS)]
    sunset = [(day0 + timedelta(days=i)).strftime("%Y-%m-%dT21:00") for i in range(DAYS)]

    return {
        "timezone": "Europe/Amsterdam",
        "current": {
            "time": hourly_times[0],
            "temperature": 15.0,
            "windspeed": 3.2,
            "winddirection": 220,
            "is_day": 1,
            "precipitation": 0.0,
            "weather_code": current_weather_code,
            "apparent_temperature": 14.0,
        },
        "daily": {
            "time": daily_times,
            "weathercode": [0] * DAYS,
            "temperature_2m_max": [18.0] * DAYS,
            "temperature_2m_min": [10.0] * DAYS,
            "sunrise": sunrise,
            "sunset": sunset,
        },
        "hourly": {
            "time": hourly_times,
            "temperature_2m": [15.0] * HOURS,
            "precipitation": [0.0] * HOURS,
            "precipitation_probability": [0] * HOURS,
            "relative_humidity_2m": [70] * HOURS,
            "surface_pressure": [1013] * HOURS,
            "visibility": [15000] * HOURS,
            "snowfall": [0.0] * HOURS,
            "weather_code": [0] * HOURS,
        },
    }


DRY_PAYLOAD = _make_payload(current_weather_code=0)     # "01d" - clear
WET_PAYLOAD = _make_payload(current_weather_code=95)    # "11d" - already a thunderstorm icon


def _run_fetch_snapshot(config, forecast_payload, station_reading):
    orig_fetch = weather_data._get_open_meteo_data
    orig_adapter = weather_data.STATION_ADAPTERS.get("generic_http")
    weather_data._get_open_meteo_data = lambda *a, **k: forecast_payload
    weather_data.STATION_ADAPTERS["generic_http"] = lambda config: station_reading
    try:
        return weather_data.fetch_snapshot(config)
    finally:
        weather_data._get_open_meteo_data = orig_fetch
        weather_data.STATION_ADAPTERS["generic_http"] = orig_adapter


class _FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.content = repr(body).encode()

    def json(self):
        return self._body


def _fetch_generic_http_with_fake_response(body, status_code=200):
    """Exercises _fetch_station_generic_http's real HTTP+parsing path
    (not just StationConditions construction) by faking requests.get - the
    only way to cover payload-shape bugs (non-dict body, wrong-typed
    fields) that the higher-level fetch_snapshot tests below can't reach,
    since those inject an already-constructed StationConditions."""
    config = DisplayConfig(station_enabled=True, station_type="generic_http", station_base_url="http://fake-station.local/")
    orig_get = weather_data.requests.get
    weather_data.requests.get = lambda *a, **k: _FakeResponse(status_code, body)
    try:
        return weather_data._fetch_station_generic_http(config)
    finally:
        weather_data.requests.get = orig_get


def test_non_dict_payload_fails_soft():
    """A bare JSON array (or any non-object body) must not crash - this was
    a real bug: payload.get(...) on a list raises AttributeError, uncaught
    by _fetch_station_generic_http's except clause."""
    return _fetch_generic_http_with_fake_response([1, 2, 3]) is None


def test_wrong_typed_field_values_fail_soft_per_field():
    """A field present with the wrong JSON type (e.g. a string instead of a
    number) must degrade to None for that field, not crash later at
    round(station_temp) in fetch_snapshot - this was a real bug (no
    exception inside the adapter itself, since dict.get() doesn't
    validate types)."""
    result = _fetch_generic_http_with_fake_response({"temperature": "warm", "rain_mm": 2.0})
    return result is not None and result.temperature_c is None and result.rain_mm == 2.0


def test_bool_field_value_treated_as_invalid():
    """bool is a subclass of int in Python - True/False must not silently
    become 1.0/0.0 for a numeric reading."""
    result = _fetch_generic_http_with_fake_response({"temperature": True, "rain_mm": False})
    return result is not None and result.temperature_c is None and result.rain_mm is None


def test_missing_fields_are_none_not_a_crash():
    result = _fetch_generic_http_with_fake_response({})
    return result is not None and result.temperature_c is None and result.rain_mm is None


def test_valid_payload_still_parses_correctly():
    result = _fetch_generic_http_with_fake_response({"temperature": 12.5, "rain_mm": 0.8})
    return result.temperature_c == 12.5 and result.rain_mm == 0.8


def test_disabled_never_calls_adapter():
    """Default config (station_enabled=False) must never call the adapter
    at all - confirms the seam is fully inert unless explicitly turned on."""
    reading = weather_data.StationConditions(temperature_c=99.0, rain_mm=99.0)
    data = _run_fetch_snapshot(DISABLED_CONFIG, DRY_PAYLOAD, reading)
    return data.current_rain_mm is None and data.current_temp == 15 and data.current_icon_key == "01d"


def test_full_reading_overrides_temp_and_icon_when_model_dry():
    reading = weather_data.StationConditions(temperature_c=12.3, rain_mm=2.0)
    data = _run_fetch_snapshot(ENABLED_CONFIG, DRY_PAYLOAD, reading)
    return data.current_temp == 12 and data.current_rain_mm == 2.0 and data.current_icon_key == "53d"


def test_rain_override_does_not_clobber_model_already_wet_icon():
    """Per "if not already showing" - a model icon that already depicts
    precipitation (here: thunderstorm, weather_code 95 -> "11d") must not be
    swapped to a plain rain icon just because the station also reports rain."""
    reading = weather_data.StationConditions(temperature_c=12.3, rain_mm=2.0)
    data = _run_fetch_snapshot(ENABLED_CONFIG, WET_PAYLOAD, reading)
    return data.current_icon_key == "11d"


def test_adapter_returns_none_fails_soft():
    data = _run_fetch_snapshot(ENABLED_CONFIG, DRY_PAYLOAD, None)
    return data.current_rain_mm is None and data.current_temp == 15 and data.current_icon_key == "01d"


def test_partial_reading_temp_only_no_icon_change():
    reading = weather_data.StationConditions(temperature_c=8.0, rain_mm=None)
    data = _run_fetch_snapshot(ENABLED_CONFIG, DRY_PAYLOAD, reading)
    return data.current_temp == 8 and data.current_rain_mm is None and data.current_icon_key == "01d"


def test_partial_reading_rain_only_falls_back_to_model_temp():
    reading = weather_data.StationConditions(temperature_c=None, rain_mm=1.5)
    data = _run_fetch_snapshot(ENABLED_CONFIG, DRY_PAYLOAD, reading)
    return data.current_temp == 15 and data.current_rain_mm == 1.5 and data.current_icon_key == "53d"


def test_intensity_thresholds():
    cases = [(0.3, "51d"), (0.5, "51d"), (0.51, "53d"), (4.0, "53d"), (4.01, "09d"), (20.0, "09d")]
    for rate, expected in cases:
        got = weather_data._apply_station_rain_override("01d", rate)
        if got != expected:
            print(f"      threshold mismatch: rain_mm={rate} expected={expected} got={got}")
            return False
    return True


def test_zero_or_missing_rain_never_overrides():
    for rate in (None, 0, -1.0):
        if weather_data._apply_station_rain_override("01d", rate) != "01d":
            return False
    return True


TESTS = [
    test_non_dict_payload_fails_soft,
    test_wrong_typed_field_values_fail_soft_per_field,
    test_bool_field_value_treated_as_invalid,
    test_missing_fields_are_none_not_a_crash,
    test_valid_payload_still_parses_correctly,
    test_disabled_never_calls_adapter,
    test_full_reading_overrides_temp_and_icon_when_model_dry,
    test_rain_override_does_not_clobber_model_already_wet_icon,
    test_adapter_returns_none_fails_soft,
    test_partial_reading_temp_only_no_icon_change,
    test_partial_reading_rain_only_falls_back_to_model_temp,
    test_intensity_thresholds,
    test_zero_or_missing_rain_never_overrides,
]


def main():
    assets = AssetStore(ICON_DIR, FONT_DIR)
    results = []

    for test in TESTS:
        try:
            ok = test()
        except Exception as e:
            ok = False
            print(f"FAIL  {test.__name__:55s} raised {e!r}")
        else:
            print(f"{'OK' if ok else 'FAIL':6s}{test.__name__}")
        results.append((test.__name__, ok))

    # Render both disabled/enabled configs in every screen mode - the real
    # visual check for the width/clipping risk a station-supplied
    # temperature/icon swap could introduce (worst case: double-digit
    # negative temp + a rain icon).
    for name, config, payload, reading in [
        ("disabled", DISABLED_CONFIG, DRY_PAYLOAD, weather_data.StationConditions(temperature_c=99.0, rain_mm=99.0)),
        ("enabled_light_rain", ENABLED_CONFIG, DRY_PAYLOAD, weather_data.StationConditions(temperature_c=6.0, rain_mm=0.3)),
        ("enabled_heavy_rain_cold", ENABLED_CONFIG, DRY_PAYLOAD, weather_data.StationConditions(temperature_c=-3.0, rain_mm=12.0)),
    ]:
        data = _run_fetch_snapshot(config, payload, reading)
        for mode in SCREEN_MODES:
            image = WeatherCanvas(assets, config, mode).render(data)
            out_path = os.path.join(OUT_DIR, f"{name}_{mode}.png")
            MockDriver(out_path).show(image)

    print("\n--- Summary ---")
    for name, ok in results:
        print(f"{'OK' if ok else 'FAIL':8s} {name}")

    if not all(ok for _, ok in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
