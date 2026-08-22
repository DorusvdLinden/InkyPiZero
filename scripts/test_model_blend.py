"""Deterministic coverage for weather_data._merge_model_series/_merge_model_blend
- not part of the app. Open-Meteo's multi-model `models=` request does not
auto-merge (each variable comes back suffixed per model, e.g.
"temperature_2m_dwd_icon_d2"), confirmed empirically against the live API for
this project's Sittard coordinates; this fakes that suffixed-response shape
directly (crafted fixtures, no network) rather than relying on live data to
land on a specific horizon boundary on any given run. Run after any change to
weather_data.py's MODEL_PRIORITY, _merge_model_series, or _merge_model_blend.
"""

import os
import sys

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)
os.chdir(REPO_DIR)

import weather_data

D2, EU, BM = weather_data.MODEL_PRIORITY  # ["dwd_icon_d2", "dwd_icon_eu", "best_match"]


def _hourly_block(n, d2_horizon, eu_horizon):
    """A "temperature_2m"-only suffixed hourly block, n hours long, where
    dwd_icon_d2 is real for [0, d2_horizon) and null after, dwd_icon_eu is
    real for [0, eu_horizon) and null after, and best_match is real for the
    entire window (matches the live-confirmed shape: best_match is the
    full-horizon model)."""
    return {
        "time": list(range(n)),
        f"temperature_2m_{D2}": [100 + i if i < d2_horizon else None for i in range(n)],
        f"temperature_2m_{EU}": [200 + i if i < eu_horizon else None for i in range(n)],
        f"temperature_2m_{BM}": [300 + i for i in range(n)],
    }


def test_within_d2_horizon_picks_d2():
    block = _hourly_block(n=10, d2_horizon=54, eu_horizon=123)
    merged = weather_data._merge_model_series(block, ["temperature_2m"])
    return merged["temperature_2m"][0] == 100 and merged["temperature_2m"][5] == 105


def test_boundary_hour_53_still_d2():
    block = _hourly_block(n=60, d2_horizon=54, eu_horizon=123)
    merged = weather_data._merge_model_series(block, ["temperature_2m"])
    return merged["temperature_2m"][53] == 100 + 53


def test_boundary_hour_54_falls_to_eu():
    block = _hourly_block(n=60, d2_horizon=54, eu_horizon=123)
    merged = weather_data._merge_model_series(block, ["temperature_2m"])
    return merged["temperature_2m"][54] == 200 + 54


def test_mid_range_picks_eu():
    block = _hourly_block(n=130, d2_horizon=54, eu_horizon=123)
    merged = weather_data._merge_model_series(block, ["temperature_2m"])
    return merged["temperature_2m"][100] == 200 + 100


def test_boundary_hour_122_still_eu():
    block = _hourly_block(n=130, d2_horizon=54, eu_horizon=123)
    merged = weather_data._merge_model_series(block, ["temperature_2m"])
    return merged["temperature_2m"][122] == 200 + 122


def test_boundary_hour_123_falls_to_best_match():
    block = _hourly_block(n=130, d2_horizon=54, eu_horizon=123)
    merged = weather_data._merge_model_series(block, ["temperature_2m"])
    return merged["temperature_2m"][123] == 300 + 123


def test_tail_beyond_both_picks_best_match():
    block = _hourly_block(n=168, d2_horizon=54, eu_horizon=123)
    merged = weather_data._merge_model_series(block, ["temperature_2m"])
    return merged["temperature_2m"][167] == 300 + 167


def test_out_of_domain_falls_through_entire_series():
    """d2/eu return null for every hour (location outside DWD's coverage) -
    every hour must fall through to best_match, with zero special-casing."""
    block = _hourly_block(n=48, d2_horizon=0, eu_horizon=0)
    merged = weather_data._merge_model_series(block, ["temperature_2m"])
    return all(merged["temperature_2m"][i] == 300 + i for i in range(48))


def test_missing_model_key_treated_as_null():
    """A suffixed model key with a null-filled array (rather than a value
    at every index) must not crash the walk and must fall through to the
    next model in priority order - the "key entirely absent" variant of
    this is covered separately by test_one_model_dropped_others_still_suffixed."""
    block = {
        "time": [0, 1, 2],
        f"temperature_2m_{D2}": [None, None, None],
        f"temperature_2m_{EU}": [None, None, None],
        f"temperature_2m_{BM}": [300, 301, 302],
    }
    merged = weather_data._merge_model_series(block, ["temperature_2m"])
    return merged["temperature_2m"] == [300, 301, 302]


def test_only_one_model_valid_falls_back_to_unsuffixed_key():
    """Confirmed live for a non-European location (Phoenix): once only one
    of the requested models is actually valid there, Open-Meteo drops
    per-model suffixing entirely and returns the plain unsuffixed key
    instead of "<var>_best_match" - no suffixed keys exist in the block at
    all."""
    block = {
        "time": [0, 1, 2],
        "temperature_2m": [45.8, 44.4, 41.9],
    }
    merged = weather_data._merge_model_series(block, ["temperature_2m"])
    return merged["temperature_2m"] == [45.8, 44.4, 41.9]


def test_one_model_dropped_others_still_suffixed():
    """Confirmed live for Reykjavik: dwd_icon_d2 (out of its domain) is
    dropped from the response entirely, while dwd_icon_eu/best_match stay
    suffixed - not a null-filled dwd_icon_d2 array, an absent key. The walk
    must fall through past the missing model straight to the next one in
    MODEL_PRIORITY, and must NOT fall back to a plain key that doesn't
    exist in this shape."""
    block = {
        "time": [0, 1, 2],
        f"temperature_2m_{EU}": [13.1, 13.0, 12.7],
        f"temperature_2m_{BM}": [12.5, 12.3, 12.8],
    }
    merged = weather_data._merge_model_series(block, ["temperature_2m"])
    return merged["temperature_2m"] == [13.1, 13.0, 12.7]


def test_merge_model_blend_current_passes_through_untouched():
    """The `current` block is never suffixed (Open-Meteo returns one
    unsuffixed block sourced from whichever model is listed first) -
    _merge_model_blend must pass it through as-is, not attempt to merge it."""
    raw = {
        "timezone": "Europe/Amsterdam",
        "current": {"time": "2026-08-22T08:00", "temperature": 14.4},
        "hourly": _hourly_block(n=5, d2_horizon=5, eu_horizon=5),
        "daily": {
            "time": [0, 1],
            f"weathercode_{D2}": [1, None],
            f"weathercode_{EU}": [2, 2],
            f"weathercode_{BM}": [3, 3],
        },
    }
    merged = weather_data._merge_model_blend(raw)
    return merged["current"] == {"time": "2026-08-22T08:00", "temperature": 14.4}


def test_merge_model_blend_daily_uses_same_priority_walk():
    raw = {
        "timezone": "Europe/Amsterdam",
        "current": {},
        "hourly": _hourly_block(n=1, d2_horizon=1, eu_horizon=1),
        "daily": {
            "time": [0, 1, 2],
            f"weathercode_{D2}": [1, None, None],
            f"weathercode_{EU}": [None, 2, None],
            f"weathercode_{BM}": [9, 9, 3],
        },
    }
    merged = weather_data._merge_model_blend(raw)
    return merged["daily"]["weathercode"] == [1, 2, 3]


TESTS = [
    test_within_d2_horizon_picks_d2,
    test_boundary_hour_53_still_d2,
    test_boundary_hour_54_falls_to_eu,
    test_mid_range_picks_eu,
    test_boundary_hour_122_still_eu,
    test_boundary_hour_123_falls_to_best_match,
    test_tail_beyond_both_picks_best_match,
    test_out_of_domain_falls_through_entire_series,
    test_missing_model_key_treated_as_null,
    test_only_one_model_valid_falls_back_to_unsuffixed_key,
    test_one_model_dropped_others_still_suffixed,
    test_merge_model_blend_current_passes_through_untouched,
    test_merge_model_blend_daily_uses_same_priority_walk,
]


def main():
    results = []
    for test in TESTS:
        try:
            ok = test()
        except Exception as e:
            ok = False
            print(f"FAIL  {test.__name__:50s} raised {e!r}")
        else:
            print(f"{'OK' if ok else 'FAIL':6s}{test.__name__}")
        results.append((test.__name__, ok))

    print("\n--- Summary ---")
    for name, ok in results:
        print(f"{'OK' if ok else 'FAIL':8s} {name}")

    if not all(ok for _, ok in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
