"""Static temperature/rain chart, replacing the Chart.js line+bar chart in
weather.html. Draws directly into the target region of the main canvas
(unlike the gauge widgets, this one doesn't need its own scratch image since
there's no rotation/scaling involved)."""

import math
from PIL import Image, ImageDraw

from widgets.icons import thicken_icon
from widgets.palette import PALETTE

LEFT_MARGIN = 58  # fits the larger axis-number font's widest label ("-36°C")
RIGHT_MARGIN = 82  # fits the widest rain-intensity label ("motrgn") at font_axis, worst case across both font families
TOP_MARGIN = 12
BOTTOM_MARGIN = 44
ICON_SIZE = 30

# precip_label values (weather_data._classify_precip) whose series is in mm/h -
# eligible for intensity-word axis labels instead of a raw number.
INTENSITY_LABELED_PRECIP = ("Regen [mm]", "Hagel [mm]")

# Rain-intensity bands (mm/h) -> Dutch label; upper bound exclusive, 50+ is "hevig".
RAIN_INTENSITY_BANDS = [
    (0.01, "droog"),
    (1.0, "motrgn"),
    (2.5, "licht"),
    (10.0, "matig"),
    (50.0, "zwaar"),
]


def _rain_intensity_label(mm_per_hour: float) -> str:
    for upper, label in RAIN_INTENSITY_BANDS:
        if mm_per_hour < upper:
            return label
    return "hevig"


def _format_rain_number_int(v: float) -> str:
    """Rounded to a whole number, no decimal - used for the non-eligible
    (category mode / snow / dry) axis-extreme label, which still rounds an
    axis-ceiling value. See _format_rain_gridline_value for the shared
    temp/rain gridlines' exact-lattice value, which never needs rounding."""
    return str(round(v))


# Minimum value the rain axis must reach at the true top of the plot (the
# max_temp position), per explicit user ask - replaces the old
# max(1, ceil(real max rain)) 1mm placeholder floor with a more generous
# 3mm minimum, so a dry/near-dry day still shows a properly-scaled axis
# instead of a near-zero one.
MIN_RAIN_AXIS_TOP_MM = 3.0

# Clean, human-readable mm-per-gridline increments, smallest first -
# _choose_rain_step scans this ascending and returns the first one that
# clears both the floor and the no-clipping requirement (see below).
# Decade-by-decade [1,2,5] pattern, except the 1-10 decade also gets an
# extra "3" (so the 3mm floor escalates minimally rather than jumping
# straight to 5), and everything below 1 is capped at 0.5 - the next step
# down, 0.2, was verified (see docs/changes.md) to be mathematically
# unreachable even at the coldest temperature ever recorded on Earth
# (Vostok Station, Antarctica, -89.2degC), so it's not included. 0.5 itself
# is only reachable on an entire day at or below 0degC with a low around
# -60degC or colder - real, if rare, for extreme-cold climates.
CANDIDATE_RAIN_STEPS_MM = (
    0.5,
    1, 2, 3, 5,
    10, 20, 50,
    100, 200, 500,
    1000, 2000, 5000,
)


def _rain_step_top_value(rain_step, grid_start, grid_step, max_temp):
    """The rain value that would sit at the true top of the plot (the
    max_temp position) for a candidate rain_step -
    plot_y0/plot_h-independent (same trick the old rain_axis_max search
    used), so this can run before those exist. steps_of_headroom =
    (max_temp - grid_start)/grid_step is the (not necessarily whole)
    number of gridline-gaps between the bottom gridline and the true top
    of the plot."""
    return rain_step * (max_temp - grid_start) / grid_step


def _choose_rain_step(rains, grid_start, grid_step, max_temp):
    """Picks the smallest candidate rain_step (mm per gridline gap) such
    that every gridline's rain value - defined directly as
    steps_above_bottom * rain_step, never interpolated against the real
    min/max temps and never rounded - reads as a properly-scaled, never-
    clipped axis. Escalates upward (bounded to CANDIDATE_RAIN_STEPS_MM)
    until BOTH:
    1. the value at the true top of the plot is >= MIN_RAIN_AXIS_TOP_MM
       (replaces the old 1mm placeholder floor), and
    2. the real day's max rain doesn't get clipped above the plot top
       (i.e. the top-of-plot value is also >= the real max rain).
    Both conditions are monotonically easier to satisfy as rain_step
    grows, so a single ascending scan (first match wins) is correct - no
    two-tier fallback needed the way the old distinct/uniform search
    required.

    Degenerate guard: if max_temp <= grid_start, there's no positive
    headroom above the bottom gridline (e.g. an all-exactly-0-degrees day,
    or a sub-one-gridline-step day) - just return the smallest candidate.
    In practice render_chart never reaches this branch: it only calls
    _choose_rain_step when rain_axis_expansion_eligible is True, and that
    now requires max_temp > grid_start itself (see render_chart - a render
    with zero headroom falls back to the ceiling-based scale instead,
    since the exact-lattice anchor would otherwise map rain values off the
    top of the plot). Kept as a defensive fallback for any other caller."""
    if max_temp - grid_start <= 0:
        return CANDIDATE_RAIN_STEPS_MM[0]
    required_top = max(MIN_RAIN_AXIS_TOP_MM, max(rains, default=0.0))
    for step in CANDIDATE_RAIN_STEPS_MM:
        if _rain_step_top_value(step, grid_start, grid_step, max_temp) >= required_top - 1e-9:
            return step
    return CANDIDATE_RAIN_STEPS_MM[-1]


def _rain_gridline_value(v, grid_start, grid_step, rain_step):
    """The exact rain value AT a temp gridline v - defined directly as
    (number of gridline-gaps above the bottom gridline) * rain_step, never
    interpolated against the real min/max temps and never rounded. v and
    grid_start are always exact multiples of grid_step by construction (see
    render_chart), so steps_above_bottom is always a whole number."""
    return (v - grid_start) / grid_step * rain_step


def _rain_step_needs_decimal(rain_step) -> bool:
    """Decimal display is a property of the chosen step itself, not a
    per-line collision fallback (there's nothing left to collide - see
    _rain_gridline_value's docstring): a step below 1mm needs one decimal
    place to be meaningful, a step of 1mm or more never does."""
    return rain_step < 1


def _format_rain_gridline_value(value, rain_step) -> str:
    """One decimal iff the chosen step itself is fractional; otherwise a
    plain whole number - see _rain_step_needs_decimal. Consecutive
    gridline values differ by exactly rain_step, so two gridlines can
    never round to the same displayed string."""
    if _rain_step_needs_decimal(rain_step):
        return f"{value:.1f}"
    return str(round(value))


def _vertical_text(draw_target: Image.Image, position, text, font, color):
    """Pastes text rotated 90 degrees (bottom-to-top), left edge at `position`."""
    bbox = font.getbbox(text)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if w <= 0 or h <= 0:
        return
    txt_img = Image.new("RGBA", (w + 2, h + 2), (0, 0, 0, 0))
    ImageDraw.Draw(txt_img).text((-bbox[0], -bbox[1]), text, font=font, fill=color)
    rotated = txt_img.rotate(90, expand=True)
    x, y = position
    draw_target.paste(rotated, (int(x), int(y - rotated.height // 2)), rotated)


def _dotted_horizontal(draw, y, plot_x0, plot_x1, color, width=2):
    x = plot_x0
    while x < plot_x1:
        draw.line([(x, y), (min(x + 5, plot_x1), y)], fill=color, width=width)
        x += 9


def render_chart(image: Image.Image, region, hourly, sun_events, text_color, icon_lookup,
                  graph_icon_step, font_small, font_axis, unit_label_temp, precip_label,
                  show_temp_gridlines: bool = False, rain_axis_format: str = "mm"):
    draw = ImageDraw.Draw(image)
    n = len(hourly)
    if n == 0:
        return

    plot_x0 = region.x + LEFT_MARGIN
    plot_x1 = region.right - RIGHT_MARGIN
    plot_y0 = region.y + TOP_MARGIN
    plot_y1 = region.bottom - BOTTOM_MARGIN
    plot_w = plot_x1 - plot_x0
    plot_h = plot_y1 - plot_y0

    temps = [h.temperature for h in hourly]
    rains = [h.rain or 0 for h in hourly]
    actual_min, actual_max = min(temps), max(temps)
    min_temp, max_temp = min(actual_min, 0), max(actual_max, 0)
    temp_span = (max_temp - min_temp) or 1
    # Cheap to compute unconditionally (pure temp math) even though only
    # show_temp_gridlines mode draws the actual dotted lines at these -
    # needed early so _choose_rain_step's search (below) can run before
    # plot_y0/plot_h/y_rain even exist.
    #
    # Narrow-swing fallback (per explicit user ask): a day whose temps
    # never cross a multiple of 10, or cross only one, would otherwise get
    # at most 1 gridline - not enough to read a rain scale off of. In that
    # case, fall back to a 5-degree grid for this render instead, usually
    # giving 2-3 reference lines (an even narrower day - within one
    # 5-degree bucket of 0, e.g. -3degC to +4degC - still gets only 1).
    # This is a temp-gridline-density fix independent of the rain-axis
    # logic below - it also benefits snow/dry windows' temp lines, which
    # never go through the rain-eligible branch. See the headroom guard on
    # rain_axis_expansion_eligible below for a related edge case this
    # narrow band can also trigger on the rain side.
    grid_start10 = math.ceil(min_temp / 10) * 10
    grid_end10 = math.floor(max_temp / 10) * 10
    standard_count = int((grid_end10 - grid_start10) / 10) + 1 if grid_end10 >= grid_start10 else 0
    if standard_count <= 1:
        grid_step = 5
        grid_start = math.ceil(min_temp / 5) * 5
        grid_end = math.floor(max_temp / 5) * 5
    else:
        grid_step = 10
        grid_start, grid_end = grid_start10, grid_end10
    # Rain/hail windows (mm/h), when rain_axis_format="category" (a
    # DisplayConfig/web-UI setting - "mm" is the default), label the rain
    # axis with intensity words instead of raw numbers. Snow (cm/h, a
    # different unit) and dry windows always keep the plain numeric axis
    # regardless of the setting.
    show_intensity_labels = rain_axis_format == "category" and precip_label in INTENSITY_LABELED_PRECIP
    # Whether show_temp_gridlines mode also labels each gridline with a
    # rain value at that height (below) - scoped to rain/hail only (both
    # "mm" and "category" format). Snow's cm values and dry's meaningless
    # placeholder-vs-nothing numbers have no self-explanatory unit/word the
    # way rain/hail's numbers or category words do, so those two keep the
    # chart's original gridline-mode behavior (temp-only gridlines, side
    # label always shown) rather than gaining unlabeled bare numbers.
    show_rain_gridline_labels = precip_label in INTENSITY_LABELED_PRECIP
    # The exact-lattice logic (see _choose_rain_step) only applies where
    # plain-number gridline labels actually get drawn. Category mode's
    # intensity words and snow/dry's absent gridline numbers use the
    # natural (real-data) max unchanged, via the old axis-ceiling scheme.
    #
    # `max_temp > grid_start` is a genuine correctness requirement, not
    # just a cosmetic gate: the lattice anchors 0mm at y_temp(grid_start)
    # and increases upward from there, which only maps onto the plot
    # correctly when grid_start sits below max_temp with real headroom.
    # On a narrow day squeezed inside a single grid_step-degree window
    # (temp_span < grid_step - e.g. an entire day between -3degC and
    # -0.7degC, common in a freezing-rain scenario), grid_start can land
    # AT max_temp itself (the plot's true top), which would otherwise
    # anchor 0mm at plot_y0 and map every positive rain value to a
    # negative, off-canvas y - a real bug caught via direct testing (a
    # zero-rain hour drew a full-plot-height bar, a 2mm hour drew a bar
    # top hundreds of pixels above the entire image). Falling back to the
    # non-eligible ceiling-based scale in this residual case keeps bars
    # correctly bounded within the plot, at the cost of exact gridline
    # labeling for that one squeezed render - an accepted residual limit,
    # not a regression (this scenario never had gridline-accurate labels
    # under any design; it now safely renders instead of corrupting).
    rain_axis_expansion_eligible = (
        show_temp_gridlines and show_rain_gridline_labels and not show_intensity_labels
        and max_temp > grid_start
    )
    if rain_axis_expansion_eligible:
        rain_step = _choose_rain_step(rains, grid_start, grid_step, max_temp)
    else:
        rain_axis_max = max(1, math.ceil(max(rains, default=0)))

    band = plot_w / n
    xs = [plot_x0 + band * (i + 0.5) for i in range(n)]

    def y_temp(v):
        return plot_y0 + (max_temp - v) / temp_span * plot_h

    if rain_axis_expansion_eligible:
        # Exact lattice: y_rain(0) is anchored to the bottom gridline's own
        # pixel row (y_temp(grid_start)), extended continuously via a fixed
        # pixels-per-gridline ratio - not a ratio against a single ceiling
        # value, so a real rain value maps to the same pixel a gridline
        # showing that exact value would sit at (see docs/changes.md for
        # the algebraic proof).
        px_per_gridline = grid_step * plot_h / temp_span
        y_grid_start = y_temp(grid_start)

        def y_rain(v):
            return y_grid_start - (v / rain_step) * px_per_gridline
    else:
        def y_rain(v):
            return plot_y0 + (rain_axis_max - v) / rain_axis_max * plot_h

    y_zero = y_temp(0)

    # rain bars - skip anything too small to be a meaningful bar, otherwise the
    # highlight strip alone (drawn at a fixed height) reads as a solid false
    # floor across hours with essentially no rain
    for x, rain in zip(xs, rains):
        top = y_rain(rain)
        if (plot_y1 - top) < 0.03 * plot_h:
            continue
        w = band * 0.85
        draw.rectangle([x - w / 2, top, x + w / 2, plot_y1], fill=(*PALETTE.chart_cool, 130))
        draw.rectangle([x - w / 2, top, x + w / 2, min(top + 3, plot_y1)], fill=(*PALETTE.chart_cool, 230))

    # temperature line, colored per segment by sign
    curve = [(x, y_temp(t)) for x, t in zip(xs, temps)]
    for (x1, y1), (x2, y2), t1, t2 in zip(curve, curve[1:], temps, temps[1:]):
        color = PALETTE.chart_warm if (t1 + t2) >= 0 else PALETTE.chart_cool
        draw.line([(x1, y1), (x2, y2)], fill=color, width=5, joint="curve")

    # Widest rain NUMBER actually drawn anywhere in the right-side column -
    # interior gridline values (mm format only) and/or the top/bottom
    # axis-extreme numbers (tracked further down) - the side label's x
    # position is pushed past this so the two never occupy the same
    # horizontal band, since the vertical label spans the plot's full
    # height and a number can land anywhere in it. Category-format
    # intensity words are handled separately (always suppress the side
    # label instead - see below), not folded into this.
    max_rain_number_w = 0

    # Set True below whenever a gridline sits close enough to the top/bottom
    # axis extreme that its label would otherwise collide with that
    # extreme's own axis-extreme label (below) - not just an *exact*
    # coincidence, a near-miss (e.g. max_temp=21, a v=20 tick) still overlaps
    # into illegible garbled text at this font size. In that case the
    # gridline's label wins (it carries the shared temp+rain reading) and the
    # corresponding axis-extreme label is skipped instead, rather than the
    # other way around.
    suppress_max_temp_label = False
    suppress_min_temp_label = False
    suppress_max_rain_label = False
    suppress_min_rain_label = False

    if show_temp_gridlines:
        # "Screen B" alternate: a uniform reference grid every 10deg across
        # the whole visible range, instead of calling out the day's actual
        # min/max. Each line gets its value labeled at the left axis (before
        # the line, matching the axis-extreme labels' own position/style).
        # Sized off font_axis, since both this gridline label and the
        # axis-extreme label it might replace draw in that font.
        label_bbox = font_axis.getbbox("0123456789°C-")
        min_label_gap = (label_bbox[3] - label_bbox[1]) * 1.2
        max_temp_y, min_temp_y = y_temp(max_temp), y_temp(min_temp)
        # loop-invariant - unit_label_temp never changes per iteration
        unit_w = font_axis.getbbox(unit_label_temp)[2]
        # grid_start/grid_end/grid_step computed earlier, before
        # _choose_rain_step needed them.
        v = grid_start
        while v <= grid_end:
            y = y_temp(v)
            _dotted_horizontal(draw, y, plot_x0, plot_x1, PALETTE.chart_zero_line)
            near_max = abs(y - max_temp_y) < min_label_gap
            near_min = abs(y - min_temp_y) < min_label_gap
            suppress_max_temp_label = suppress_max_temp_label or near_max
            suppress_min_temp_label = suppress_min_temp_label or near_min
            # Rain-side proximity is checked against plot_y0/plot_y1 directly
            # (always the true rain-axis extremes by construction) rather
            # than max_temp_y/min_temp_y - those normally coincide exactly
            # with plot_y0/plot_y1 too, but temp_span's "or 1" fallback
            # (above) can decouple them from plot_y0/plot_y1 on a degenerate
            # all-temps-exactly-0 window, which would otherwise wrongly hide
            # a rain-axis label that isn't actually colliding with anything.
            near_max_rain = abs(y - plot_y0) < min_label_gap
            near_min_rain = abs(y - plot_y1) < min_label_gap

            # shifted left by the pixel width of the axis-extreme labels'
            # unit suffix ("C", not present here) so the numbers themselves
            # line up in a column - a space character isn't the same width
            # as the letter it's standing in for, so padding with literal
            # spaces would leave them misaligned.
            label = f"{v}°"
            draw.text((plot_x0 - 6 - unit_w, y), label, font=font_axis, fill=PALETTE.chart_zero_line, anchor="rm")

            # show_intensity_labels always draws (its ceiling-based
            # rain_axis_max is always well-defined); the plain-number
            # lattice path only draws when rain_axis_expansion_eligible -
            # on the rare narrow-range render where that's False (see the
            # headroom guard above), this gridline gets no rain label at
            # all, same treatment as snow/dry - the axis-extreme labels
            # (now active, since the non-eligible ceiling path is in
            # effect) carry the reading instead.
            if show_rain_gridline_labels and (show_intensity_labels or rain_axis_expansion_eligible):
                # Shared axis: temp and rain map onto the exact same
                # plot_y0..plot_y1 pixel range - label the rain value at
                # this same height instead of drawing a second independent
                # rain grid. This is a geometric scale marker like the temp
                # side. In "mm" format it's now an EXACT lattice value
                # (steps_above_bottom * rain_step, see
                # _rain_gridline_value) - never interpolated against the
                # real min/max temps and never rounded, so the line's pixel
                # position and its printed number are always exactly
                # consistent with each other.
                if show_intensity_labels:
                    rain_at_y = rain_axis_max * (1 - (y - plot_y0) / plot_h)
                    rain_label = _rain_intensity_label(rain_at_y)
                else:
                    rain_value = _rain_gridline_value(v, grid_start, grid_step, rain_step)
                    rain_label = _format_rain_gridline_value(rain_value, rain_step)
                draw.text((plot_x1 + 6, y), rain_label, font=font_axis, fill=PALETTE.chart_zero_line, anchor="lm")
                if not show_intensity_labels:
                    label_w = font_axis.getbbox(rain_label)[2]
                    max_rain_number_w = max(max_rain_number_w, label_w)
                suppress_max_rain_label = suppress_max_rain_label or near_max_rain
                suppress_min_rain_label = suppress_min_rain_label or near_min_rain
            v += grid_step
    else:
        # dashed actual min/max lines - skip whichever one exactly coincides
        # with its axis extreme (min_temp/max_temp clamp to 0, so e.g. the min
        # line sits exactly on the bottom axis whenever the actual low is
        # <=0deg) - the axis's own value label already shows that number, so a
        # second dashed line+label right on top of it is pure redundancy.
        dashed_lines = []
        if actual_max != max_temp:
            dashed_lines.append((actual_max, PALETTE.chart_warm if actual_max >= 0 else PALETTE.chart_cool))
        if actual_min != min_temp:
            dashed_lines.append((actual_min, PALETTE.chart_warm if actual_min >= 0 else PALETTE.chart_cool))
        for value, color in dashed_lines:
            y = y_temp(value)
            _dotted_horizontal(draw, y, plot_x0, plot_x1, color)
            label_dy = 14 if (plot_y1 - y) > 20 else -14
            label = f"{value}°"
            draw.text((plot_x0 + plot_w / 2, y + label_dy), label, font=font_axis, fill=color, anchor="mm")

        # black dashed 0deg reference line, only shown when the day actually
        # dips below freezing (min_temp < 0 means actual_min < 0 too, since
        # min_temp = min(actual_min, 0)) - without this there'd be no marker
        # at all for where freezing sits once the axis itself is clamped to
        # the actual (negative) low instead of 0.
        if min_temp < 0:
            _dotted_horizontal(draw, y_zero, plot_x0, plot_x1, PALETTE.chart_zero_line)
            label_dy = 14 if (plot_y1 - y_zero) > 20 else -14
            draw.text((plot_x0 + plot_w / 2, y_zero + label_dy), "0°", font=font_axis, fill=PALETTE.chart_zero_line, anchor="mm")

    # axes
    draw.line([(plot_x0, plot_y0), (plot_x0, plot_y1)], fill=text_color, width=2)
    draw.line([(plot_x1, plot_y0), (plot_x1, plot_y1)], fill=text_color, width=2)
    draw.line([(plot_x0, plot_y1), (plot_x1, plot_y1)], fill=text_color, width=2)

    # vertical dotted line marking the day boundary, aligned with the new
    # day's own hour (00:00's tick/label position, i.e. xs[i]) rather than
    # the geometric edge between the two hours' columns, so it visibly
    # lines up with whichever tick/label is actually on screen for it.
    for i, hour in enumerate(hourly):
        if hour.is_day_start:
            date_x = xs[i]
            y = plot_y0
            while y < plot_y1:
                draw.line([(date_x, y), (date_x, min(y + 5, plot_y1))], fill=text_color, width=2)
                y += 9
            break

    # unit folded directly into the axis-extreme labels ("28°C") instead of
    # a separate always-present vertical "C" label off to the side - one
    # less element competing for space, and the chart reclaims that whole
    # column (see LEFT_MARGIN).
    temp_unit_suffix = f"°{unit_label_temp}"
    if not suppress_max_temp_label:
        draw.text((plot_x0 - 6, y_temp(max_temp)), f"{max_temp}{temp_unit_suffix}", font=font_axis, fill=text_color, anchor="rm")
    if not suppress_min_temp_label:
        draw.text((plot_x0 - 6, y_temp(min_temp)), f"{min_temp}{temp_unit_suffix}", font=font_axis, fill=text_color, anchor="rm")

    # show_intensity_labels (computed above) - the actual peak/trough
    # value, not the rounded-up rain_axis_max ceiling, so the word matches
    # what really happened.
    if show_intensity_labels:
        top_label = _rain_intensity_label(max(rains))
        bottom_label = _rain_intensity_label(min(rains))
    elif not rain_axis_expansion_eligible:
        # rain_axis_max is always a whole number (the natural max(1,
        # ceil(...)) placeholder) - _format_rain_number_int makes that
        # invariant explicit. Only computed here (not in eligible mode,
        # where rain_axis_max doesn't exist and neither label is ever
        # drawn - see below).
        top_label = _format_rain_number_int(rain_axis_max)
        bottom_label = "0"
    else:
        top_label = bottom_label = None
    # On dry windows, rain_axis_max is always the max(1, ...) placeholder
    # floor (there's no real rain to size the axis off) - showing "1" up top
    # implies a rain reading that never happened, so it's dropped entirely
    # rather than suppressed only on gridline-collision grounds like the
    # other axis-extreme labels above.
    #
    # Both the top AND bottom axis-extreme labels are also dropped
    # unconditionally whenever rain_axis_expansion_eligible - per explicit
    # user ask ("no need to show actual max at the top"), the interior
    # gridlines now carry an exact, always-consistent reading of the scale
    # (see _choose_rain_step/_rain_gridline_value), so a separate
    # axis-extreme label adds nothing and can actively duplicate one: under
    # the exact lattice, y_rain(0) lands exactly on the v=grid_start
    # gridline's own pixel row, whose label is already always "0" - so an
    # un-suppressed bottom axis-extreme label would draw a second,
    # overlapping "0" on top of it. The top axis-extreme has the mirror
    # problem (it sits at the true edge of the plot, wherever max_temp
    # happens to land, not at the next lattice step, so it could show a
    # value that breaks the clean progression the interior gridlines just
    # established - a real observed case: interior gridlines "0, 3, 6" plus
    # an axis-extreme "8" a step later).
    if not rain_axis_expansion_eligible and not suppress_max_rain_label and precip_label != "Droog":
        draw.text((plot_x1 + 6, y_rain(rain_axis_max)), top_label, font=font_axis, fill=text_color, anchor="lm")
        if not show_intensity_labels:
            max_rain_number_w = max(max_rain_number_w, font_axis.getbbox(top_label)[2])
    if not rain_axis_expansion_eligible and not suppress_min_rain_label:
        draw.text((plot_x1 + 6, y_rain(0)), bottom_label, font=font_axis, fill=text_color, anchor="lm")
        if not show_intensity_labels:
            max_rain_number_w = max(max_rain_number_w, font_axis.getbbox(bottom_label)[2])

    # The precipitation label ("Regen [mm]" / "Hagel [mm]" / "Sneeuw [cm]" /
    # "Droog" - picked in weather_data.py based on the hourly window's actual
    # weather codes) sits a flat 2mm (~10px) gap off the axis line. Always
    # suppressed when show_intensity_labels ("category" format) - the
    # intensity words ("motrgn" etc, up to 60px at font_axis) are drawn as
    # the axis-extreme labels in EVERY screen mode (not just gridlines -
    # suppress_max_rain_label/suppress_min_rain_label only get set inside
    # the show_temp_gridlines branch, so in "original" mode these always
    # draw unsuppressed), and are too wide to push the side label past
    # without exceeding RIGHT_MARGIN and clipping off-canvas - confirmed via
    # a real render before this was caught as a live bug (rain_original_category.png
    # showed "Regen" overlapping "licht" - a regression from entry 51's
    # font-size bump, not present when the side label used the smaller
    # font_bold). In plain-number mode, the side label always shows,
    # positioned past the widest NUMBER actually drawn anywhere in this
    # column - gridline values (tracked above) and/or the top/bottom
    # axis-extreme numbers (tracked just above, when not suppressed) -
    # rather than a fixed offset, so it never lands on top of one
    # regardless of screen mode or where a given day's numbers fall.
    # Per explicit user ask, this also means the side label no longer needs
    # a smaller fallback font (_pick_side_label_font, entry 51) for
    # "Sneeuw [cm]" - every plain-number-mode label now renders at font_axis
    # size, consistent with the numbers next to it.
    if not show_intensity_labels:
        regen_x = plot_x1 + 6 + max_rain_number_w + 6 if max_rain_number_w else plot_x1 + 10
        _vertical_text(image, (regen_x, (plot_y0 + plot_y1) // 2), precip_label, font_axis, text_color)

    # x-axis hour labels + tick marks - same cadence as the icon strip
    # below, so each icon sits directly under its hour's label instead of
    # drifting out of sync with a differently-stepped label grid
    for i in range(0, n, graph_icon_step):
        draw.line([(xs[i], plot_y1), (xs[i], plot_y1 + 4)], fill=text_color, width=2)
        draw.text((xs[i], plot_y1 + 6), hourly[i].time_label, font=font_small, fill=text_color, anchor="ma")

    # hourly/sun-event icon strip, at a fixed row below the plot (matches the
    # original's chart.chartArea.bottom + 25 fixed placement, not following the curve)
    sun_icon_by_index = {}
    for event in sun_events:
        idx = max(0, min(round(event.position), n - 1))
        sun_icon_by_index[idx] = event.icon_key
    icon_y = plot_y1 + 18
    for i in range(n):
        icon_key = sun_icon_by_index.get(i)
        if icon_key is None and i % graph_icon_step != 0:
            continue
        icon_key = icon_key or hourly[i].icon_key
        icon = icon_lookup(icon_key, (ICON_SIZE, ICON_SIZE))
        if icon:
            icon = thicken_icon(icon)
            image.paste(icon, (int(xs[i] - ICON_SIZE / 2), icon_y), icon)
