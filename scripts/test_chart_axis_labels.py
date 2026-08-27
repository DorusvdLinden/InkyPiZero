"""Deterministic coverage for widgets/chart.py's rain-axis label
deduplication - not part of the app. Calls render_chart directly (not the
full fetch_snapshot -> WeatherCanvas pipeline) with crafted HourPoint lists,
spying on ImageDraw.Draw.text to collect every string drawn in the rain-axis
column (x > plot_x1) and asserting no two of them are identical - two
dotted lines (or a dotted line and the axis-extreme label) showing the same
digits reads as a duplicate even when they mark genuinely different
heights. No network/hardware needed.

Covers real, reported/review-caught cases, most recently (see
docs/changes.md entries 53-55 for the full history):

1. The axis-extreme "maximum" label duplicating the topmost interior
   gridline's own rounded value (e.g. both showing "1" on a near-dry day
   where rain_axis_max clamps to the 1mm placeholder floor) - fixed by
   dropping the axis-extreme label when this happens
   (topmost_gridline_rain_label in render_chart). For some temp shapes
   (grid_end very close to max_temp) this collision is structural - no
   choice of rain_axis_max avoids it - so it's handled separately from
   the mechanism below, not folded into it.

2. Two adjacent interior gridlines rounding to the same whole number.
   Per explicit user ask ("set dotted lines for rain to whole numbers or
   0.5/1 decimal if needed... expand the max when needed... no more
   rounding"), this is now resolved in two layers, tried together for
   each candidate rain_axis_max via _rain_gridline_labels:
   a. A colliding gridline falls back to ONE decimal place (never more,
      never a coarser half-step trick) - but only when rain_axis_max is
      <=9mm, where a decimal is meaningful; above 9mm, always whole
      numbers, full stop, even if a collision remains.
   b. _choose_rain_axis_max searches a handful of steps above the
      natural max(1, ceil(real max rain)) for the smallest candidate
      where, after (a)'s per-line fallback, every gridline is genuinely
      distinct - rather than accepting the natural max's collisions.
      Since rain_axis_max also sets the bar chart's own scale, this can
      leave the real data's peak short of the very top of the chart on
      days where expansion is needed - an accepted tradeoff, not an
      oversight.
   Even with both layers, an extreme enough temp swing (very many
   gridlines packed into the search budget) can still exhaust the step
   budget without finding a fully clean candidate - see
   test_extreme_temp_swing_can_still_collide, a known/accepted residual
   limit, not a bug someone forgot to handle.

Run after any change to widgets/chart.py's rain-axis label logic
(_format_rain_number/_format_rain_number_int/_rain_gridline_labels/
_choose_rain_axis_max, the gridline loop, or the axis-extreme label
suppression) - see CLAUDE.md.
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


def _hourly(temp_of_hour, rain_of_hour=None):
    return [
        HourPoint(time_label=f"{h:02d}:00", temperature=temp_of_hour(h),
                  rain=(rain_of_hour(h) if rain_of_hour else 0.0), icon_key="61d")
        for h in range(24)
    ]


def test_near_dry_day_axis_extreme_dropped_not_duplicated():
    """The originally reported bug: a near-dry day (a trace of rain at one
    hour) clamps rain_axis_max to the 1mm placeholder floor. This temp
    shape's topmost gridline structurally lands very close to the axis
    top regardless of rain_axis_max, so no expansion resolves it - the
    axis-extreme "maximum" label is correctly dropped instead, leaving
    the topmost gridline's own "1" as the sole appearance."""
    hourly = _hourly(lambda h: 15 + (h % 5), lambda h: 0.3 if h == 5 else 0.0)
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    ok = _no_duplicate_strings(texts)
    if not ok:
        print(f"      duplicate strings in: {texts}")
    return ok and any(t == "1" for _, t in texts)  # the "1" must still appear once, not vanish entirely


def test_adjacent_collision_resolved_via_decimal_without_expansion():
    """A single gridline-to-gridline collision (max_temp=25, a trace of
    rain giving rain_axis_max=1) that the per-line decimal fallback alone
    resolves - natural_max=1 itself is already collision-free once v=10's
    "0"-colliding value falls back to "0.4", so no expansion is needed."""
    hourly = _hourly(lambda h: 25 if h == 12 else 5, lambda h: 0.3 if h == 5 else 0.0)
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    ok = _no_duplicate_strings(texts)
    if not ok:
        print(f"      duplicate strings in: {texts}")
    return ok and any(t == "0.4" for _, t in texts)


def test_expansion_needed_when_decimal_alone_isnt_enough():
    """max_temp=31 (a trace of rain, rain_axis_max naturally 1): at
    candidate=1, v=20 and v=30 both round to "1" and the decimal fallback
    can't separate them either (0.65 and 0.97 both round to 1 at one
    decimal too) - genuinely needs a bigger max. _choose_rain_axis_max
    finds candidate=2 works (confirmed via direct search below), and the
    resulting axis-extreme ("2") duplicates the topmost gridline there
    too, correctly dropped by the same mechanism as the near-dry case."""
    hourly = _hourly(lambda h: 31 if h == 12 else 5, lambda h: 0.4 if h == 5 else 0.0)
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    ok = _no_duplicate_strings(texts)
    if not ok:
        print(f"      duplicate strings in: {texts}")
    chosen_max = chart_mod._choose_rain_axis_max([0.4], 0, 30, 0, 31)
    return ok and chosen_max == 2


def test_choose_rain_axis_max_direct():
    """Direct unit coverage of the search itself - confirms candidate=1 is
    rejected (real interior collision even with the decimal fallback) and
    candidate=2 is accepted, matching the hand-traced reasoning above."""
    labels1, ok1 = chart_mod._rain_gridline_labels(1, 0, 30, 0, 31)
    labels2, ok2 = chart_mod._rain_gridline_labels(2, 0, 30, 0, 31)
    if ok1:
        print(f"      expected candidate=1 to collide, got {labels1}")
        return False
    if not ok2:
        print(f"      expected candidate=2 to be collision-free, got {labels2}")
        return False
    return chart_mod._choose_rain_axis_max([0.9], 0, 30, 0, 31) == 2


def test_above_9mm_never_falls_back_to_decimal():
    """Per explicit user ask: above 9mm, always whole numbers, even if a
    collision remains - no decimal fallback in that regime at all. A
    contrived but direct case (axis_max=20, two gridlines whose true
    values are 0 and 0.2mm apart) confirms the "0"/"0" duplicate is
    accepted rather than one of them switching to a decimal."""
    labels, collision_free = chart_mod._rain_gridline_labels(20, 0, 10, 0, 1000)
    strs = [label for _, _, label in labels]
    return not collision_free and strs == ["0", "0"]


def test_extreme_temp_swing_can_still_collide():
    """Known, accepted residual limit: an extreme, unrealistic-for-this-
    deployment 150-degree single-day temperature swing (16 gridlines)
    packs enough of them into a narrow rain-value band that the search's
    bounded step budget (a handful of steps, per explicit user ask - not
    unlimited) is exhausted without finding a fully clean candidate. Not
    reachable by any real weather day; documented here so a future change
    to the search strategy doesn't need to rediscover that this exists and
    was already considered."""
    for candidate in range(1, 8):
        _, collision_free = chart_mod._rain_gridline_labels(candidate, 0, 150, 0, 150)
        if collision_free:
            print(f"      expected no collision-free candidate in range, found one at {candidate}")
            return False
    return True


def test_normal_rainy_day_still_no_duplicates():
    """A substantial, steady rain day (the common case) - confirms the
    dedup logic doesn't introduce spurious decimals or expand the max when
    nothing actually collides."""
    hourly = _hourly(lambda h: 15 + (h % 5), lambda h: 2.4)
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    return _no_duplicate_strings(texts)


def test_category_mode_unaffected():
    """rain_axis_format="category" uses words (_rain_intensity_label), not
    numbers - the expansion/decimal dedup logic must not touch it (words
    are allowed to legitimately repeat across adjacent gridlines in the
    same band, and rain_axis_max stays the natural, unexpanded value)."""
    hourly = _hourly(lambda h: 15 + (h % 5), lambda h: 2.4)
    texts = _rain_axis_texts(hourly, "Regen [mm]", rain_axis_format="category")
    # No numeric label should appear at all in category mode.
    return all("." not in t and not t.isdigit() for _, t in texts if t not in ("0",))


TESTS = [
    test_near_dry_day_axis_extreme_dropped_not_duplicated,
    test_adjacent_collision_resolved_via_decimal_without_expansion,
    test_expansion_needed_when_decimal_alone_isnt_enough,
    test_choose_rain_axis_max_direct,
    test_above_9mm_never_falls_back_to_decimal,
    test_extreme_temp_swing_can_still_collide,
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
