"""Deterministic coverage for the "Wind" data point's number - not part of
the app. Crafted Open-Meteo `current` payloads, no network/hardware needed
(live data can't reliably hit every Beaufort band on a given run).

Covers (docs/changes.md entry 60):
1. get_beaufort_number against the standard m/s breakpoints, including
   values exactly on a boundary.
2. get_beaufort_description_nl still returns the same Dutch labels after
   sharing its breakpoint table with get_beaufort_number.
3. wind_speed_unit="ms": a whole number of m/s, rounded half up
   (0.82 -> 1, 2.5 -> 3), unit "m/s".
4. wind_speed_unit="beaufort": the Beaufort number, unit "bft".
5. The description comes from the unrounded speed in both modes.
6. The UV data point's label is plain "UV-index" (no range).

Run after any change to weather_data's wind/Beaufort/UV data points or the
wind_speed_unit setting - see CLAUDE.md.
"""

import os
import sys

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)
os.chdir(REPO_DIR)

import pytz

from weather_data import _parse_data_points, get_beaufort_description_nl, get_beaufort_number

TZ = pytz.timezone("Europe/Amsterdam")


def _points(speed, unit):
    weather = {"current": {"windspeed": speed, "winddirection": 90}, "hourly": {}}
    return {dp["kind"]: dp for dp in _parse_data_points(weather, {"hourly": {}}, None, TZ, 0.0, unit)}


def test_beaufort_numbers():
    cases = {0.0: 0, 0.29: 0, 0.3: 1, 1.5: 1, 1.6: 2, 5.0: 3, 5.5: 4, 15.0: 7,
             17.2: 8, 32.69: 11, 32.7: 12, 35.0: 12}
    bad = {v: get_beaufort_number(v) for v, want in cases.items() if get_beaufort_number(v) != want}
    if bad:
        print(f"      wrong Beaufort numbers: {bad}")
        return False
    return True


def test_descriptions_unchanged():
    cases = {0.1: "Windstil", 0.82: "Zwakke wind", 6.0: "Matige wind", 12.0: "Krachtige wind",
             26.0: "Zware storm", 40.0: "Orkaan"}
    bad = {v: get_beaufort_description_nl(v) for v, want in cases.items() if get_beaufort_description_nl(v) != want}
    if bad:
        print(f"      wrong descriptions: {bad}")
        return False
    return True


def test_ms_mode_whole_numbers():
    for speed, want in ((0.82, 1), (1.71, 2), (2.5, 3), (0.4, 0), (5.22, 5)):
        dp = _points(speed, "ms")["wind"]
        if dp["measurement"] != want or dp["unit"] != "m/s":
            print(f"      {speed} m/s -> {dp['measurement']} {dp['unit']}, want {want} m/s")
            return False
    return True


def test_beaufort_mode():
    for speed, want in ((0.82, 1), (5.0, 3), (15.0, 7), (35.0, 12)):
        dp = _points(speed, "beaufort")["wind"]
        if dp["measurement"] != want or dp["unit"] != "bft":
            print(f"      {speed} m/s -> {dp['measurement']} {dp['unit']}, want {want} bft")
            return False
    return True


def test_description_uses_raw_speed():
    # 0.35 shows as "0 m/s" but is Beaufort 1; 3.45 shows as "3 m/s" but is
    # Beaufort 3 - a description from the rounded value would be wrong.
    for unit in ("ms", "beaufort"):
        for speed, want in ((0.35, "Zwakke wind"), (3.45, "Matige wind")):
            dp = _points(speed, unit)["wind"]
            if dp["label"] != want:
                print(f"      {unit}: expected {want!r} for {speed} m/s, got {dp['label']!r}")
                return False
    return True


def test_uv_label_has_no_range():
    label = _points(1.0, "ms")["uv"]["label"]
    if label != "UV-index":
        print(f"      expected 'UV-index', got {label!r}")
        return False
    return True


TESTS = [
    test_beaufort_numbers,
    test_descriptions_unchanged,
    test_ms_mode_whole_numbers,
    test_beaufort_mode,
    test_description_uses_raw_speed,
    test_uv_label_has_no_range,
]


def main():
    results = []
    for test in TESTS:
        try:
            ok = test()
        except Exception as e:
            ok = False
            print(f"FAIL  {test.__name__:55s} raised {e!r}")
        else:
            print(f"{'OK' if ok else 'FAIL':6s}{test.__name__}")
        results.append(ok)
    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
