"""Deterministic coverage for widgets/chart.py's rain-axis label
deduplication - not part of the app. Calls render_chart directly (not the
full fetch_snapshot -> WeatherCanvas pipeline) with crafted HourPoint lists,
spying on ImageDraw.Draw.text to collect every string drawn in the rain-axis
column (x > plot_x1) and asserting no two of them are identical - two
dotted lines (or a dotted line and the axis-extreme label) showing the same
digits reads as a duplicate even when they mark genuinely different
heights. No network/hardware needed.

Covers real, reported/review-caught cases, most recently (see
docs/changes.md entries 53-56 for the full history):

1. The axis-extreme "maximum" label duplicating the topmost interior
   gridline's own rounded value (e.g. both showing "1" on a near-dry day
   where rain_axis_max clamps to the 1mm placeholder floor) - originally
   fixed by dropping the axis-extreme label specifically when it
   collided; now moot, since #4 below means the axis-extreme is never
   drawn in gridlines mode at all.

2. Two adjacent interior gridlines rounding to the same whole number.
   Resolved in two layers, tried together for each candidate
   rain_axis_max via _rain_gridline_labels:
   a. A colliding gridline falls back to ONE decimal place (never more)
      - but only when rain_axis_max is <=DECIMAL_ELIGIBLE_MAX_MM (10mm);
      above that, always whole numbers, full stop, even if a collision
      remains.
   b. _choose_rain_axis_max searches a handful of integer steps above the
      natural max(1, ceil(real max rain)) - rather than accepting the
      natural max's collisions.

3. A second, distinct problem from #2, caught via a real reported case:
   even when every gridline's label is individually distinct, evenly
   spaced gridlines can show UNEVENLY spaced numbers if each is rounded
   independently (e.g. true values 0, 2.33, 4.67, 7 -> "0, 2, 5, 7",
   steps of 2/3/2 - each number individually correct, but reading as
   inconsistent to a viewer). _rain_gridline_labels now also reports
   whether consecutive displayed values differ by a *constant* amount
   ("uniform"), and _choose_rain_axis_max prefers the smallest candidate
   that's both distinct AND uniform - deliberately expanding past the
   real data's max to buy "headspace" for a clean, evenly-stepped axis,
   per explicit user ask ("expand the max when needed... create
   headspace... no need to show actual max at the top").

4. Even with clean, uniform interior gridlines, a SEPARATE axis-extreme
   label at the true top of the plot doesn't necessarily continue that
   pattern - when grid_end < max_temp (the temp range isn't a clean
   multiple of 10), the axis-extreme sits a real pixel gap above the
   topmost interior gridline and can show a value that breaks the clean
   step just established (e.g. interior "0, 3, 6" plus an axis-extreme
   "8" right after). Per explicit user ask ("no need to show actual max
   at the top"), the axis-extreme label is now never drawn at all in
   gridlines mode for plain-number rain/hail windows - the interior
   gridlines alone carry the reading.

Even with all of this, an extreme enough temp swing (very many gridlines
packed into the search budget) can still exhaust the step budget without
finding a fully clean candidate - see
test_extreme_temp_swing_can_still_collide, a known/accepted residual
limit, not a bug someone forgot to handle.

Run after any change to widgets/chart.py's rain-axis label logic
(_format_rain_number/_format_rain_number_int/_rain_gridline_labels/
_choose_rain_axis_max/DECIMAL_ELIGIBLE_MAX_MM, the gridline loop, or the
axis-extreme label suppression) - see CLAUDE.md.
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
    top regardless of rain_axis_max. The axis-extreme "maximum" label is
    never drawn at all in gridlines mode now (see
    test_gridlines_mode_never_shows_separate_top_extreme) - so this can't
    reappear as a duplicate - leaving the topmost gridline's own "1" as
    the sole appearance."""
    hourly = _hourly(lambda h: 15 + (h % 5), lambda h: 0.3 if h == 5 else 0.0)
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    ok = _no_duplicate_strings(texts)
    if not ok:
        print(f"      duplicate strings in: {texts}")
    return ok and any(t == "1" for _, t in texts)  # the "1" must still appear once, not vanish entirely


def test_gridlines_mode_never_shows_separate_top_extreme():
    """A second real reported bug, found right after the headspace-
    expansion fix above: even with clean, uniform interior gridlines, the
    SEPARATE axis-extreme label at the true top of the plot doesn't
    necessarily continue that pattern. This fixture (temps 0-29, not a
    clean multiple of 10, so grid_end=20 sits a real pixel gap below the
    actual max_temp=29) confirmed pre-this-branch: with only the
    distinct-only search (no uniform preference yet), rain_axis_max
    stayed at the natural 7mm (0,2,5 already distinct, no expansion
    needed) - but with the uniform-step preference (the fix above) it
    instead expands to 8mm for the interior gridlines' sake ("0, 3, 6"),
    and the un-dropped axis-extreme would then show "8" right after "6" -
    breaking the clean step it just established (worse than before this
    file's own fix above, if the axis-extreme removal below weren't also
    applied). Per explicit user ask ("no need to show actual max at the
    top"), the axis-extreme is now never drawn in this mode at all -
    confirmed here by checking the exact count of labels shown equals
    exactly the 3 interior gridlines (0, 3, 6), not 4."""
    hourly = _hourly(lambda h: 29 if h == 12 else 0, lambda h: 7.0 if h == 5 else 0.0)
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    values = sorted(int(t) for _, t in texts)
    if values != [0, 3, 6]:
        print(f"      expected exactly [0, 3, 6] (no separate top extreme), got {texts}")
        return False
    return True


def test_uneven_steps_resolved_via_headspace_expansion():
    """The real reported follow-up bug: a day with temps 0-30 and 7mm real
    max rain naturally gives rain_axis_max=7, whose evenly-spaced
    gridlines (raw values 0, 2.33, 4.67, 7) round independently to
    "0, 2, 5, 7" - individually correct, but unevenly stepped (2, 3, 2).
    _choose_rain_axis_max now finds axis_max=9 instead - not the smallest
    *distinct* candidate (7 is already distinct), but the smallest
    distinct-AND-uniform one, buying headspace (7mm of real data inside a
    9mm-scaled axis) for a clean "0, 3, 6, 9" reading."""
    hourly = _hourly(lambda h: 30 if h == 12 else 0, lambda h: 7.0 if h == 5 else 0.0)
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    values = sorted(int(t) for _, t in texts)
    if values != [0, 3, 6, 9]:
        print(f"      expected [0, 3, 6, 9], got {texts}")
        return False
    chosen_max = chart_mod._choose_rain_axis_max([7.0], 0, 30, 0, 30)
    return chosen_max == 9


def test_decimal_fallback_still_prefers_uniform_steps():
    """A day with temps 0-20 and a trace of rain (natural max 1mm) - the
    per-line decimal fallback alone already produces a clean, uniform
    "0, 0.5, 1" (step of exactly 0.5 throughout), so no expansion is
    needed - confirms the decimal fallback and the uniform-step
    preference compose correctly, not just the whole-number path."""
    hourly = _hourly(lambda h: 20 if h == 12 else 0, lambda h: 0.4 if h == 5 else 0.0)
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    ok = _no_duplicate_strings(texts)
    if not ok:
        print(f"      duplicate strings in: {texts}")
    values = sorted(float(t) for _, t in texts)
    return ok and values == [0.0, 0.5, 1.0]


def test_choose_rain_axis_max_direct():
    """Direct unit coverage of the search itself, on the max_temp=31 case
    that originally exposed the axis-extreme-vs-search-collision bug
    (docs/changes.md entry 55) - confirms candidate=1 still collides
    (real interior collision even with the decimal fallback) and the
    search now lands on candidate=3 (the smallest DISTINCT+UNIFORM
    candidate - "0,1,2,3" - not candidate=2 from before this entry, which
    was merely distinct but unevenly stepped)."""
    labels1, distinct1, _uniform1 = chart_mod._rain_gridline_labels(1, 0, 30, 0, 31)
    if distinct1:
        print(f"      expected candidate=1 to collide, got {labels1}")
        return False
    labels3, distinct3, uniform3 = chart_mod._rain_gridline_labels(3, 0, 30, 0, 31)
    if not (distinct3 and uniform3):
        print(f"      expected candidate=3 to be distinct and uniform, got {labels3}")
        return False
    return chart_mod._choose_rain_axis_max([0.9], 0, 30, 0, 31) == 3


def test_above_threshold_never_falls_back_to_decimal():
    """Per explicit user ask: above DECIMAL_ELIGIBLE_MAX_MM (10mm), always
    whole numbers, even if a collision remains - no decimal fallback in
    that regime at all. A contrived but direct case (axis_max=20, two
    gridlines whose true values are 0 and 0.2mm apart) confirms the
    "0"/"0" duplicate is accepted rather than one of them switching to a
    decimal."""
    assert chart_mod.DECIMAL_ELIGIBLE_MAX_MM == 10, "test assumes the 10mm threshold"
    labels, distinct, _uniform = chart_mod._rain_gridline_labels(20, 0, 10, 0, 1000)
    strs = [label for _, _, label in labels]
    return not distinct and strs == ["0", "0"]


def test_extreme_temp_swing_can_still_collide():
    """Known, accepted residual limit: an extreme, unrealistic-for-this-
    deployment 150-degree single-day temperature swing (16 gridlines)
    packs enough of them into a narrow rain-value band that the search's
    bounded step budget (a handful of steps) is exhausted without finding
    a fully DISTINCT candidate (let alone a uniform one). Not reachable by
    any real weather day; documented here so a future change to the
    search strategy doesn't need to rediscover that this exists and was
    already considered."""
    for candidate in range(1, 8):
        _, distinct, _uniform = chart_mod._rain_gridline_labels(candidate, 0, 150, 0, 150)
        if distinct:
            print(f"      expected no distinct candidate in range, found one at {candidate}")
            return False
    return True


def test_normal_rainy_day_still_no_duplicates():
    """A substantial, steady rain day (the common case) - confirms the
    dedup/uniformity logic doesn't introduce spurious decimals or expand
    the max when nothing actually needs it."""
    hourly = _hourly(lambda h: 15 + (h % 5), lambda h: 2.4)
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    return _no_duplicate_strings(texts)


def test_category_mode_unaffected():
    """rain_axis_format="category" uses words (_rain_intensity_label), not
    numbers - the expansion/decimal/uniformity logic must not touch it
    (words are allowed to legitimately repeat across adjacent gridlines in
    the same band, and rain_axis_max stays the natural, unexpanded
    value)."""
    hourly = _hourly(lambda h: 15 + (h % 5), lambda h: 2.4)
    texts = _rain_axis_texts(hourly, "Regen [mm]", rain_axis_format="category")
    # No numeric label should appear at all in category mode.
    return all("." not in t and not t.isdigit() for _, t in texts if t not in ("0",))


TESTS = [
    test_near_dry_day_axis_extreme_dropped_not_duplicated,
    test_gridlines_mode_never_shows_separate_top_extreme,
    test_uneven_steps_resolved_via_headspace_expansion,
    test_decimal_fallback_still_prefers_uniform_steps,
    test_choose_rain_axis_max_direct,
    test_above_threshold_never_falls_back_to_decimal,
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
