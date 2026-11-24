"""Deterministic coverage for the single temperature-rounding rule
(weather_data.round_half_up, docs/changes.md entry 58) - not part of the
app. No network/hardware needed.

Before entry 58 the same Open-Meteo floats were turned into whole numbers
three ways: int() for the chart's hourly temps and the forecast cards
(truncation toward zero: a -0.7 night drew as a flat 0), Python's round()
for the header (banker's rounding). Photo of the live panel, 2026-11-22:
header "-1°", chart line never below 0.

Covers:
1. round_half_up itself (halves up, no "-0").
2. The header's night low and the chart agree on a -0.7 night.
3. The chart keeps the real (unrounded) hourly temps, so a -0.7 night
   extends the axis below 0 and the printed bottom label is "-1°C".
4. A 0.3 low doesn't produce a second "0°" dashed line next to the axis's
   own "0°C" (original mode compares printed values).

Run after any change to weather_data's temperature rounding or to
widgets/chart.py's temperature labels - see CLAUDE.md.
"""

import os
import sys
from datetime import datetime

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)
os.chdir(REPO_DIR)

import pytz
from PIL import Image, ImageDraw

import widgets.chart as chart_mod
from layout import Region
from weather_data import HourPoint, _night_day_temps, round_half_up
from widgets.icons import AssetStore

ASSETS = AssetStore(os.path.join(REPO_DIR, "assets", "icons"), os.path.join(REPO_DIR, "assets", "fonts"))
FONT_SMALL = ASSETS.font("normal", 13)
FONT_AXIS = ASSETS.font("bold", 18)
CHART_REGION = Region(0, 200, 800, 160)
TZ = pytz.timezone("Europe/Amsterdam")


def _texts(hourly, gridlines):
    image = Image.new("RGB", (800, 480), "white")
    collected = []
    orig_text = ImageDraw.ImageDraw.text

    def spy_text(self, xy, text, *a, **k):
        collected.append((round(xy[0]), round(xy[1]), text))
        return orig_text(self, xy, text, *a, **k)

    ImageDraw.ImageDraw.text = spy_text
    try:
        chart_mod.render_chart(
            image, CHART_REGION, hourly, [], (0, 0, 0), lambda k, s: None, 2,
            FONT_SMALL, FONT_AXIS, "C", "Droog", show_temp_gridlines=gridlines,
        )
    finally:
        ImageDraw.ImageDraw.text = orig_text
    return collected


def _hourly(temps):
    return [HourPoint(time_label=f"{h:02d}:00", temperature=t, rain=0.0, icon_key="04d")
            for h, t in enumerate(temps)]


def test_round_half_up_values():
    cases = {-1.5: -1, -0.6: -1, -0.5: 0, -0.4: 0, 0.4: 0, 0.5: 1, 2.5: 3, 2.9: 3, -1.9: -2}
    bad = {x: round_half_up(x) for x, want in cases.items() if round_half_up(x) != want}
    if bad:
        print(f"      wrong: {bad}")
        return False
    if str(round_half_up(-0.4)) != "0":
        print("      -0.4 printed as -0")
        return False
    return True


# Night of 22->23 Nov hovering at -0.7 (the photo's case): evening 20:00 at
# +0.4, the night at -0.6..-0.7, back to +2 in the afternoon.
NIGHT_TEMPS = [0.4, 0.1, -0.3, -0.6, -0.7, -0.7, -0.6, -0.6, -0.5, -0.4, -0.2, 0.3,
               0.9, 1.6, 2.0, 2.0, 1.4, 0.8, 0.5, 0.3, 0.2, 0.1, 0.0, -0.1]


def test_header_and_chart_agree_on_night_low():
    now = TZ.localize(datetime(2026, 11, 22, 20, 0))
    times = [f"2026-11-22T{h:02d}:00" for h in range(20, 24)] + [f"2026-11-23T{h:02d}:00" for h in range(0, 20)]
    hourly_data = {"time": times, "temperature_2m": NIGHT_TEMPS}
    daily = {"sunrise": ["2026-11-22T08:05", "2026-11-23T08:07"], "sunset": ["2026-11-22T16:40", "2026-11-23T16:39"]}
    _, next_night_low = _night_day_temps(hourly_data, daily, TZ, now)
    chart_min = round_half_up(min(NIGHT_TEMPS))
    if next_night_low != -1 or chart_min != -1:
        print(f"      header night low {next_night_low}, chart min {chart_min}, both should be -1")
        return False
    return True


def test_chart_axis_goes_below_zero_on_minus_0_7_night():
    """Original mode: the axis bottom is the real low, printed "-1°C".
    Gridlines mode: the bottom snaps down to the next gridline (entry 59),
    so a -0.7 low gives a "-5°" bottom gridline - either way below 0."""
    for gridlines, want in ((False, "-1°C"), (True, "-5°")):
        texts = _texts(_hourly(NIGHT_TEMPS), gridlines)
        left = [t for x, _, t in texts if x < 60]
        if want not in left:
            print(f"      gridlines={gridlines}: expected a {want!r} bottom label, left labels {left}")
            return False
    return True


def test_no_duplicate_zero_line_for_small_positive_low():
    temps = [0.3 + (h % 12) * 0.5 for h in range(24)]  # low 0.3, high 5.8
    texts = _texts(_hourly(temps), gridlines=False)
    zeros = [t for _, _, t in texts if t in ("0°", "0°C")]
    if zeros != ["0°C"]:
        print(f"      expected only the axis '0°C', got {zeros}")
        return False
    return True


TESTS = [
    test_round_half_up_values,
    test_header_and_chart_agree_on_night_low,
    test_chart_axis_goes_below_zero_on_minus_0_7_night,
    test_no_duplicate_zero_line_for_small_positive_low,
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
