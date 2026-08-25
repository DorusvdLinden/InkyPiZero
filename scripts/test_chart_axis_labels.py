"""Deterministic coverage for widgets/chart.py's rain-axis label
deduplication - not part of the app. Calls render_chart directly (not the
full fetch_snapshot -> WeatherCanvas pipeline) with crafted HourPoint lists,
spying on ImageDraw.Draw.text to collect every string drawn in the rain-axis
column (x > plot_x1) and asserting no two of them are identical - two
dotted lines (or a dotted line and the axis-extreme label) showing the same
digits reads as a duplicate even when they mark genuinely different
heights. No network/hardware needed.

Covers three real, reported/review-caught cases:
1. The axis-extreme "maximum" label duplicating the topmost interior
   gridline's own rounded value (e.g. both showing "1" on a near-dry day
   where rain_axis_max clamps to the 1mm placeholder floor) - fixed by
   dropping the axis-extreme label when this happens.
2. Two adjacent interior gridlines rounding to the same whole number -
   fixed by showing a decimal on whichever gridline actually needs it,
   instead of always rounding to a bare integer.
3. A fresh-context review caught a gap in fix 2: one decimal place can
   itself round right back to the same whole number (e.g. 0.97 -> "1"
   again via the trailing-zero-drop in "{round(v,1):g}") - fixed by
   escalating to two decimals only when one wasn't enough
   (_disambiguate_rain_number).

Run after any change to widgets/chart.py's rain-axis label logic
(_format_rain_number/_format_rain_number_int/_disambiguate_rain_number,
the gridline loop, or the axis-extreme label suppression) - see CLAUDE.md.
"""

import os
import sys

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)
os.chdir(REPO_DIR)

from PIL import Image, ImageDraw

import widgets.chart as chart_mod
from weather_data import HourPoint
from widgets.icons import AssetStore
from layout import Region

ICON_DIR = os.path.join(REPO_DIR, "assets", "icons")
FONT_DIR = os.path.join(REPO_DIR, "assets", "fonts")

ASSETS = AssetStore(ICON_DIR, FONT_DIR)
FONT_SMALL = ASSETS.font("normal", 13)
FONT_AXIS = ASSETS.font("bold", 18)

CHART_REGION = Region(0, 200, 800, 160)  # matches layout.CHART_AREA's height


def _rain_axis_texts(hourly, precip_label, rain_axis_format="mm"):
    """Renders once and returns every (y, text) drawn right of the plot
    (the rain-axis column - gridline values + axis-extreme labels), sorted
    by y. Doesn't care about x precision, just that x is past the plot."""
    image = Image.new("RGB", (800, 480), "white")
    collected = []
    orig_text = ImageDraw.ImageDraw.text

    def spy_text(self, xy, text, *a, **k):
        if xy[0] > CHART_REGION.right - 90:  # right-side column only, not the left temp axis
            collected.append((round(xy[1]), text))
        return orig_text(self, xy, text, *a, **k)

    ImageDraw.ImageDraw.text = spy_text
    try:
        chart_mod.render_chart(
            image, CHART_REGION, hourly, [], (0, 0, 0), lambda k, s: None, 2,
            FONT_SMALL, FONT_AXIS, "C", precip_label,
            show_temp_gridlines=True, rain_axis_format=rain_axis_format,
        )
    finally:
        ImageDraw.ImageDraw.text = orig_text
    return sorted(collected)


def _no_duplicate_strings(texts):
    strings = [t for _, t in texts]
    return len(strings) == len(set(strings))


def test_near_dry_day_no_duplicate_axis_max():
    """Real reported case: a near-dry day (a trace of rain at one hour)
    clamps rain_axis_max to the 1mm placeholder floor. A wide-ish temp
    range puts the topmost interior gridline far enough from the top in
    PIXELS to dodge the existing proximity-based suppression, but its
    rounded rain value can still land on the exact same "1" as the
    axis-extreme label."""
    hourly = [
        HourPoint(time_label=f"{h:02d}:00", temperature=15 + (h % 5),
                  rain=(0.3 if h == 5 else 0.0), icon_key="61d")
        for h in range(24)
    ]
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    ok = _no_duplicate_strings(texts)
    if not ok:
        print(f"      duplicate strings in: {texts}")
    return ok and any(t == "1" for _, t in texts)  # the "1" must still appear once, not vanish entirely


def test_wide_temp_range_adjacent_gridlines_get_decimals():
    """Many gridlines (wide temp range) over a small rain_axis_max packs
    several of them into a narrow rain-value band - several adjacent pairs
    would round to the same whole number without the decimal fallback."""
    hourly = [
        HourPoint(time_label=f"{h:02d}:00", temperature=(h * 2),
                  rain=(0.3 if h == 5 else 0.0), icon_key="61d")
        for h in range(24)
    ]
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    ok = _no_duplicate_strings(texts)
    if not ok:
        print(f"      duplicate strings in: {texts}")
    # Confirm the fallback actually engaged (at least one decimal-formatted
    # label present) - otherwise this test would trivially pass even if the
    # fallback were deleted, as long as nothing happened to collide today.
    has_decimal = any("." in t for _, t in texts)
    return ok and has_decimal


def test_one_decimal_still_colliding_escalates_to_two():
    """A real gap caught by review: one decimal place can itself round
    back to the same whole number it was supposed to disambiguate from
    (e.g. 0.97 rounds to 1.0 at one decimal, and the trailing ".0" gets
    dropped, producing "1" again) - silently reintroducing the exact
    duplicate the fallback exists to prevent. Found via brute-force search
    over realistic integer temperatures/rain_axis_max combinations
    (max_temp=31, a trace of rain giving rain_axis_max=1) - the topmost
    gridline (v=30) needs the 2-decimal escalation specifically."""
    hourly = [
        HourPoint(time_label=f"{h:02d}:00", temperature=(31 if h == 12 else 5),
                  rain=(0.4 if h == 5 else 0.0), icon_key="61d")
        for h in range(24)
    ]
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    ok = _no_duplicate_strings(texts)
    if not ok:
        print(f"      duplicate strings in: {texts}")
    has_two_decimal_place_label = any(len(t.split(".")[-1]) == 2 for _, t in texts if "." in t)
    return ok and has_two_decimal_place_label


def test_normal_rainy_day_still_no_duplicates():
    """A substantial, steady rain day (the common case) - confirms the
    dedup logic doesn't introduce spurious decimals or drop labels when
    nothing actually collides."""
    hourly = [
        HourPoint(time_label=f"{h:02d}:00", temperature=15 + (h % 5),
                  rain=2.4, icon_key="63d")
        for h in range(24)
    ]
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    return _no_duplicate_strings(texts)


def test_category_mode_unaffected():
    """rain_axis_format="category" uses words (_rain_intensity_label), not
    numbers - the numeric dedup logic must not touch it (words are allowed
    to legitimately repeat across adjacent gridlines in the same band)."""
    hourly = [
        HourPoint(time_label=f"{h:02d}:00", temperature=15 + (h % 5),
                  rain=2.4, icon_key="63d")
        for h in range(24)
    ]
    texts = _rain_axis_texts(hourly, "Regen [mm]", rain_axis_format="category")
    # No numeric label should appear at all in category mode.
    return all("." not in t and not t.isdigit() for _, t in texts if t not in ("0",))


TESTS = [
    test_near_dry_day_no_duplicate_axis_max,
    test_wide_temp_range_adjacent_gridlines_get_decimals,
    test_one_decimal_still_colliding_escalates_to_two,
    test_normal_rainy_day_still_no_duplicates,
    test_category_mode_unaffected,
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
        results.append((test.__name__, ok))

    print("\n--- Summary ---")
    for name, ok in results:
        print(f"{'OK' if ok else 'FAIL':8s} {name}")

    if not all(ok for _, ok in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
