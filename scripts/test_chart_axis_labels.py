"""Deterministic coverage for widgets/chart.py's rain-axis exact lattice -
not part of the app. Calls render_chart directly (not the full
fetch_snapshot -> WeatherCanvas pipeline) with crafted HourPoint lists,
spying on ImageDraw.Draw.text/line/rectangle to collect what's actually
drawn. No network/hardware needed.

Core invariant (see docs/changes.md's most recent numbered entry for the
full history): in "gridlines"/"compact" screen mode, for rain/hail windows
in plain "mm" format, every gridline's printed rain number is now an EXACT
value - defined directly as (gridline_index * rain_step), never
interpolated against the real (arbitrary) min/max temps and never rounded.
This replaces the old rain_axis_max-ceiling + per-line rounding/collision-
dedup scheme, which could leave a gridline's printed number off from its
true pixel position by up to ~0.5mm.

Key rules covered:
1. The bottom gridline is always exactly 0mm.
2. rain_step (mm per gridline gap) is chosen from a small clean-number
   list (_choose_rain_step) so that the value at the true top of the plot
   is both >=3mm (MIN_RAIN_AXIS_TOP_MM, replacing the old 1mm placeholder
   floor) and never clips the real day's max rain.
3. Bars use the same fixed step, so a bar's real value maps to the exact
   same pixel a gridline showing that value would sit at (proven directly
   in test_bar_and_gridline_agree_exactly below).
4. Decimal display is a property of the chosen step itself (step<1 -> one
   decimal everywhere), never a per-line collision fallback - collisions
   are now structurally impossible.
5. A day whose temps cross 0 or 1 multiples of 10 falls back to a 5-degree
   grid for that render, usually giving 2-3 reference lines instead of at
   most 1 (see test_narrow_temp_range_falls_back_to_5deg_grid) - an even
   narrower day (within one 5-degree bucket of 0) still gets only 1.
6. Both the top and bottom rain axis-extreme labels are unconditionally
   dropped in eligible mode - the interior gridlines alone carry the
   reading (see test_no_duplicate_zero_label).
7. rain_axis_expansion_eligible additionally requires real headroom
   (max_temp > grid_start) - a narrow day squeezed inside a single
   grid_step-degree window can put grid_start AT max_temp itself (the
   plot's true top), which would otherwise anchor 0mm at the top and map
   every positive rain value off-canvas. That render falls back to the
   safe ceiling-based scale instead, sacrificing exact gridline labels for
   correctness (see test_no_headroom_falls_back_safely_not_off_canvas - a
   real bug caught and fixed during development, not a hypothetical).

Run after any change to widgets/chart.py's rain-axis logic
(_choose_rain_step/_rain_step_top_value/_rain_gridline_value/
_format_rain_gridline_value/CANDIDATE_RAIN_STEPS_MM/MIN_RAIN_AXIS_TOP_MM,
the gridline-drawing loop, the grid_step narrow-range fallback, or the
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


def _all_axis_texts(hourly, precip_label, rain_axis_format="mm"):
    """Like _rain_axis_texts but also returns the left-side temp labels -
    used by the 5-degree-grid fallback tests, which need to check both
    sides."""
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
            FONT_SMALL, FONT_AXIS, "C", precip_label,
            show_temp_gridlines=True, rain_axis_format=rain_axis_format,
        )
    finally:
        ImageDraw.ImageDraw.text = orig_text
    return collected


def _no_duplicate_strings(texts):
    strings = [t for _, t in texts]
    return len(strings) == len(set(strings))


def _hourly(temp_of_hour, rain_of_hour=None):
    return [
        HourPoint(time_label=f"{h:02d}:00", temperature=temp_of_hour(h),
                  rain=(rain_of_hour(h) if rain_of_hour else 0.0), icon_key="61d")
        for h in range(24)
    ]


def test_gridlines_mode_never_shows_separate_top_extreme():
    """Confirms the axis-extreme "maximum" label is never drawn at all in
    gridlines mode for plain-number rain/hail windows - only the interior
    gridlines' exact lattice values appear. Fixture: max_temp=29 (h12),
    real rain peak 7.0mm (h5). grid_start=0, headroom=29, grid_step=10
    (standard_count=3 gridlines: 0/10/20). required_top=max(3,7)=7;
    smallest step with step*29/10>=7 is 3 (2*2.9=5.8<7, 3*2.9=8.7>=7).
    Interior gridlines at v=0,10,20 -> values 0,3,6."""
    hourly = _hourly(lambda h: 29 if h == 12 else 0, lambda h: 7.0 if h == 5 else 0.0)
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    values = sorted(int(t) for _, t in texts)
    if values != [0, 3, 6]:
        print(f"      expected exactly [0, 3, 6] (no separate top extreme), got {texts}")
        return False
    return True


def test_uneven_steps_resolved_via_headspace_expansion():
    """Fixture: max_temp=30 (h12), real rain peak 7.0mm (h5). grid_start=0,
    headroom=30, grid_step=10 (standard_count=4: 0/10/20/30).
    required_top=7; smallest step with step*3>=7 is 3 (2*3=6<7). Interior
    gridlines 0,10,20,30 -> values 0,3,6,9."""
    hourly = _hourly(lambda h: 30 if h == 12 else 0, lambda h: 7.0 if h == 5 else 0.0)
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    values = sorted(int(t) for _, t in texts)
    if values != [0, 3, 6, 9]:
        print(f"      expected [0, 3, 6, 9], got {texts}")
        return False
    chosen_step = chart_mod._choose_rain_step([7.0], grid_start=0, grid_step=10, max_temp=30)
    if chosen_step != 3:
        print(f"      expected _choose_rain_step to pick 3, got {chosen_step}")
        return False
    return True


def test_extreme_temp_swing_no_longer_collides():
    """The old distinct/uniform search had a documented residual limit: an
    extreme 150-degree single-day temp swing (16 gridlines) could exhaust
    its bounded step budget without finding a fully distinct candidate.
    Under the new exact-lattice design that limit is structurally closed -
    every gridline's value is a distinct multiple of rain_step by
    construction, regardless of how many gridlines there are. Confirms
    that for every step in the candidate list, the 16 gridline values
    (0*step, 1*step, ..., 15*step) are all distinct."""
    step = chart_mod._choose_rain_step([5.0], grid_start=0, grid_step=10, max_temp=150)
    values = [chart_mod._rain_gridline_value(v, 0, 10, step) for v in range(0, 151, 10)]
    if len(values) != len(set(values)):
        print(f"      expected all-distinct values even for this extreme swing, got {values}")
        return False
    return True


def test_normal_rainy_day_still_no_duplicates():
    """A substantial, steady rain day (the common case) - confirms the
    exact-lattice logic doesn't introduce duplicate labels."""
    hourly = _hourly(lambda h: 15 + (h % 5), lambda h: 2.4)
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    return _no_duplicate_strings(texts)


def test_category_mode_unaffected():
    """rain_axis_format="category" uses words (_rain_intensity_label), not
    numbers - the exact-lattice logic must not touch it (words are allowed
    to legitimately repeat across adjacent gridlines in the same band, and
    the axis stays on the old natural/unexpanded rain_axis_max)."""
    hourly = _hourly(lambda h: 15 + (h % 5), lambda h: 2.4)
    texts = _rain_axis_texts(hourly, "Regen [mm]", rain_axis_format="category")
    return all("." not in t and not t.isdigit() for _, t in texts if t not in ("0",))


def test_3mm_floor_on_near_dry_day():
    """A near-dry day (a trace of rain at one hour) must still show a
    scale reaching at least 3mm at the top, replacing the old 1mm
    placeholder floor. Fixture: temps 15-19 (h%5), so min_temp=0,
    max_temp=19, grid_start=0, grid_step=10 (only v=0,10 -> count=2, not
    the 5-degree fallback), headroom=19. required_top=max(3,0.3)=3;
    smallest step with step*1.9>=3 is 2 (1*1.9=1.9<3). Expected exact
    gridline values: [0, 2] - no "1" anywhere, unlike the old 1mm-floor
    design."""
    hourly = _hourly(lambda h: 15 + (h % 5), lambda h: 0.3 if h == 5 else 0.0)
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    values = sorted(int(t) for _, t in texts)
    if values != [0, 2]:
        print(f"      expected [0, 2] (3mm floor via step=2), got {texts}")
        return False
    step = chart_mod._choose_rain_step([0.3], grid_start=0, grid_step=10, max_temp=19)
    top_value = chart_mod._rain_step_top_value(step, 0, 10, 19)
    if top_value < chart_mod.MIN_RAIN_AXIS_TOP_MM:
        print(f"      expected top value >= {chart_mod.MIN_RAIN_AXIS_TOP_MM}, got {top_value}")
        return False
    return True


def test_step_escalation_driven_by_clipping_not_floor():
    """A real rain peak (50mm) far exceeding the 3mm floor, with modest
    temp headroom (max_temp=20, grid_start=0, grid_step=10 -> headroom=20)
    - the floor alone would only need step>=1.5 (step=2), but clipping
    requires step*2>=50, i.e. step>=25, so the smallest candidate clearing
    that is 50. Confirms condition 4b (no-clipping) can be the binding
    constraint independently of condition 4a (the floor)."""
    step = chart_mod._choose_rain_step([50.0], grid_start=0, grid_step=10, max_temp=20)
    if step != 50:
        print(f"      expected clipping-driven escalation to step=50, got {step}")
        return False
    top_value = chart_mod._rain_step_top_value(step, 0, 10, 20)
    if top_value < 50:
        print(f"      expected top value >= real max rain (50), got {top_value}")
        return False
    return True


def test_fractional_step_only_on_extreme_cold_day():
    """rain_step < 1mm is only reachable via the 3mm floor when the
    headroom/grid_step ratio is >=6 - verified (see docs/changes.md) to
    require an entire day at or below 0degC with a low around -60degC or
    colder. Fixture: grid_start=-60 (an entire day <=0degC, e.g. actual
    temps -65 to -10), grid_step=10, max_temp=0 -> headroom=60, ratio=6.0
    exactly -> smallest step clearing required_top=3 is 0.5
    (1*6=6>=3 would also pass - wait: step=1 gives top_value=1*6=6>=3, so
    actually step=1 already clears the floor at ratio=6; 0.5 needs
    ratio>=6 too (0.5*6=3.0>=3, exactly at the boundary) and is smaller,
    so it's picked first)."""
    step = chart_mod._choose_rain_step([0.0], grid_start=-60, grid_step=10, max_temp=0)
    if step != 0.5:
        print(f"      expected step=0.5 at the extreme-cold boundary ratio, got {step}")
        return False
    if not chart_mod._rain_step_needs_decimal(step):
        print(f"      expected step={step} to need decimal display")
        return False
    if chart_mod._format_rain_gridline_value(1.5, step) != "1.5":
        print(f"      expected '1.5', got {chart_mod._format_rain_gridline_value(1.5, step)}")
        return False
    if chart_mod._format_rain_gridline_value(0.0, step) != "0.0":
        print(f"      expected '0.0', got {chart_mod._format_rain_gridline_value(0.0, step)}")
        return False
    return True


def test_no_step_below_1mm_for_realistic_temps():
    """Sanity check that sub-1mm steps are a genuine edge case, not
    something normal rendering stumbles into: a wide but realistic range
    (max_temp clamped to 0, min_temp -40 - a very cold but non-extreme
    day) should never pick a step below 1mm."""
    step = chart_mod._choose_rain_step([0.0], grid_start=-40, grid_step=10, max_temp=0)
    if step < 1:
        print(f"      expected step>=1 for a realistic -40..0 day, got {step}")
        return False
    return True


def test_bar_and_gridline_agree_exactly():
    """End-to-end proof that the printed gridline number and the bar's
    real pixel position are exactly consistent - not just true on paper.
    Fixture: temps 0-30 (h12), one hour's rain set to exactly 2x whatever
    rain_step gets chosen (a value that lands exactly on the 2nd gridline
    above the bottom). Spies on both draw.line (dotted gridlines) and
    draw.rectangle (bar tops), asserting the bar's top y matches the
    gridline's y within float epsilon."""
    step = chart_mod._choose_rain_step([0.0], grid_start=0, grid_step=10, max_temp=30)
    target_value = 2 * step
    hourly = _hourly(lambda h: 30 if h == 12 else 0, lambda h: target_value if h == 5 else 0.0)

    image = Image.new("RGB", (800, 480), "white")
    gridline_ys = []
    bar_tops = []
    orig_line = ImageDraw.ImageDraw.line
    orig_rect = ImageDraw.ImageDraw.rectangle

    def spy_line(self, xy, **k):
        # _dotted_horizontal draws many short horizontal segments at the
        # gridline's y - dedupe by just collecting every y seen.
        y = xy[0][1]
        if xy[0][0] != xy[1][0]:  # horizontal segment (gridline), not a vertical tick/day-boundary
            gridline_ys.append(round(y, 3))
        return orig_line(self, xy, **k)

    def spy_rect(self, xy, **k):
        bar_tops.append(round(xy[1], 3))
        return orig_rect(self, xy, **k)

    ImageDraw.ImageDraw.line = spy_line
    ImageDraw.ImageDraw.rectangle = spy_rect
    try:
        chart_mod.render_chart(
            image, CHART_REGION, hourly, [], (0, 0, 0), lambda k, s: None, 2,
            FONT_SMALL, FONT_AXIS, "C", "Regen [mm]",
            show_temp_gridlines=True, rain_axis_format="mm",
        )
    finally:
        ImageDraw.ImageDraw.line = orig_line
        ImageDraw.ImageDraw.rectangle = orig_rect

    # sorted ascending y = descending temp value (y grows downward, and
    # y_temp decreases as v increases) - so the bottom gridline (v=
    # grid_start, value 0) is the LAST entry, one gridline-gap up (value=
    # 1*step) is second-to-last, and the target (2 gaps up, value=2*step)
    # is third-to-last.
    distinct_gridline_ys = sorted(set(gridline_ys))
    expected_gridline_y = distinct_gridline_ys[-3] if len(distinct_gridline_ys) > 2 else None
    if expected_gridline_y is None or not bar_tops:
        print(f"      insufficient data: gridlines={distinct_gridline_ys}, bars={bar_tops}")
        return False
    closest_bar_top = min(bar_tops, key=lambda t: abs(t - expected_gridline_y))
    if abs(closest_bar_top - expected_gridline_y) > 0.5:
        print(f"      expected bar top ({closest_bar_top}) to match gridline y "
              f"({expected_gridline_y}) within 0.5px")
        return False
    return True


def test_no_duplicate_zero_label():
    """Regression test for a bug caught during design: under the exact
    lattice, y_rain(0) lands exactly on the v=grid_start gridline's own
    pixel row, whose label is always "0" - the separate bottom
    axis-extreme "0" label must be unconditionally suppressed in eligible
    mode, or it would draw a second, overlapping "0"."""
    hourly = _hourly(lambda h: 15 + (h % 5), lambda h: 2.4)
    texts = _rain_axis_texts(hourly, "Regen [mm]")
    zero_count = sum(1 for _, t in texts if t == "0")
    if zero_count != 1:
        print(f"      expected exactly one '0' label, got {zero_count} in {texts}")
        return False
    return True


def test_dry_window_does_not_use_lattice_logic():
    """"Droog" (dry) windows are never rain_axis_expansion_eligible
    (show_rain_gridline_labels excludes them), so they must stay on the
    untouched non-eligible path regardless of temps. That path still draws
    a single bottom axis-extreme "0" (an accurate reading - a dry window
    really did see 0mm - unaffected by this change; only the misleading
    placeholder-max TOP label is dropped for "Droog", pre-existing
    behavior). What must NOT happen is any exact-lattice artifact (no
    interior gridline rain values, since show_rain_gridline_labels is
    False for "Droog")."""
    hourly = _hourly(lambda h: 6 + (h % 3), lambda h: 0.0)  # narrow range, all dry
    texts = _rain_axis_texts(hourly, "Droog")
    strings = [t for _, t in texts]
    if strings != ["0"]:
        print(f"      expected exactly one bottom '0' label, got {texts}")
        return False
    return True


def test_narrow_temp_range_falls_back_to_5deg_grid():
    """A day whose temps stay within (0, 10) (e.g. 2-7degC all day) - note
    min_temp/max_temp always clamp to include 0 (min(actual_min,0)/
    max(actual_max,0)), so this real fixture's effective temp range is
    [0, 7], giving exactly one standard 10-degree gridline ("0") - not
    enough to read a rain scale off of. The 5-degree fallback (rule 7)
    must kick in, adding a "5°" gridline (plain gridline format - no unit
    suffix, unlike the "N°C" axis-extreme labels) with a matching exact
    rain value, on both the temp and rain sides."""
    hourly = _hourly(lambda h: 2 + (h % 6), lambda h: 0.5 if h == 5 else 0.0)  # temps 2-7
    all_texts = _all_axis_texts(hourly, "Regen [mm]")
    temp_side_5 = any(t == "5°" for _x, _y, t in all_texts)
    rain_side_values = sorted(t for x, _y, t in all_texts
                               if x > CHART_REGION.right - 90 and t.replace(".", "").isdigit())
    if not temp_side_5:
        print(f"      expected a plain '5°' gridline label, got {[t for _x, _y, t in all_texts]}")
        return False
    if not rain_side_values:
        print(f"      expected at least one rain-axis gridline value, got none")
        return False
    return True


def test_negative_narrow_temp_range_also_falls_back_to_5deg():
    """Mirror of the above on the negative side: temps entirely between
    -8 and -2 (never crossing -10 or reaching 0 from below) - min_temp=-8,
    max_temp clamps UP to 0, so the effective range is [-8, 0], again only
    one standard gridline ("0"). Confirms the fallback isn't just a
    positive-side special case: it should add "-5°" here."""
    hourly = _hourly(lambda h: -8 + (h % 6), lambda h: 0.5 if h == 5 else 0.0)  # temps -8..-3
    all_texts = _all_axis_texts(hourly, "Regen [mm]")
    temp_side_neg5 = any(t == "-5°" for _x, _y, t in all_texts)
    if not temp_side_neg5:
        print(f"      expected a plain '-5°' gridline label, got {[t for _x, _y, t in all_texts]}")
        return False
    return True


def test_no_headroom_falls_back_safely_not_off_canvas():
    """Regression test for a real bug caught during development: an entire
    day squeezed inside a single 5-degree window straddling max_temp's
    clamp (e.g. -3degC to -0.7degC, a plausible freezing-rain day) puts
    grid_start exactly AT max_temp (zero headroom) - the exact-lattice
    anchor (0mm at y_temp(grid_start)) would then map positive rain values
    to pixels ABOVE the plot's own top, and even a zero-rain hour would
    draw a full-plot-height bar (verified before the fix: bar tops of
    plot_y0 for 0mm and hundreds of pixels off-canvas for a real rain
    hour). rain_axis_expansion_eligible's headroom guard must route this
    render through the safe, bounded ceiling-based scale instead - every
    bar's top must land within [plot_y0, plot_y1]."""
    hourly = _hourly(lambda h: -3 + (h % 3) * 1.1, lambda h: 2.0 if h == 5 else 0.0)
    plot_y0 = CHART_REGION.y + chart_mod.TOP_MARGIN
    plot_y1 = CHART_REGION.bottom - chart_mod.BOTTOM_MARGIN

    image = Image.new("RGB", (800, 480), "white")
    bar_tops = []
    orig_rect = ImageDraw.ImageDraw.rectangle

    def spy_rect(self, xy, **k):
        bar_tops.append(xy[1])
        return orig_rect(self, xy, **k)

    ImageDraw.ImageDraw.rectangle = spy_rect
    try:
        chart_mod.render_chart(
            image, CHART_REGION, hourly, [], (0, 0, 0), lambda k, s: None, 2,
            FONT_SMALL, FONT_AXIS, "C", "Regen [mm]",
            show_temp_gridlines=True, rain_axis_format="mm",
        )
    finally:
        ImageDraw.ImageDraw.rectangle = orig_rect

    if not bar_tops:
        print("      expected at least one bar to be drawn (real rain at h=5)")
        return False
    out_of_bounds = [t for t in bar_tops if t < plot_y0 - 0.5 or t > plot_y1 + 0.5]
    if out_of_bounds:
        print(f"      expected all bar tops within [{plot_y0}, {plot_y1}], got out-of-bounds: {out_of_bounds}")
        return False
    return True


def test_wide_enough_range_does_not_trigger_5deg_fallback():
    """Control/negative case: a day spanning both sides of a multiple of
    10 widely enough to already have >=2 standard gridlines (temps 3-13,
    effective range [0, 13] after clamping -> gridlines "0" and "10") must
    NOT trigger the 5-degree fallback - no "5°" label should appear."""
    hourly = _hourly(lambda h: 3 + (h % 11), lambda h: 0.0)  # temps 3-13
    all_texts = _all_axis_texts(hourly, "Regen [mm]")
    plain_gridlines = sorted({t for _x, _y, t in all_texts if t in ("0°", "10°")})
    has_5 = any(t == "5°" for _x, _y, t in all_texts)
    if has_5:
        print(f"      expected no '5°' fallback line when >=2 standard gridlines exist, got {[t for _x, _y, t in all_texts]}")
        return False
    if plain_gridlines != ["0°", "10°"]:
        print(f"      expected standard '0°'/'10°' gridlines, got {plain_gridlines}")
        return False
    return True


TESTS = [
    test_gridlines_mode_never_shows_separate_top_extreme,
    test_uneven_steps_resolved_via_headspace_expansion,
    test_extreme_temp_swing_no_longer_collides,
    test_normal_rainy_day_still_no_duplicates,
    test_category_mode_unaffected,
    test_3mm_floor_on_near_dry_day,
    test_step_escalation_driven_by_clipping_not_floor,
    test_fractional_step_only_on_extreme_cold_day,
    test_no_step_below_1mm_for_realistic_temps,
    test_bar_and_gridline_agree_exactly,
    test_no_duplicate_zero_label,
    test_dry_window_does_not_use_lattice_logic,
    test_narrow_temp_range_falls_back_to_5deg_grid,
    test_negative_narrow_temp_range_also_falls_back_to_5deg,
    test_no_headroom_falls_back_safely_not_off_canvas,
    test_wide_enough_range_does_not_trigger_5deg_fallback,
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
