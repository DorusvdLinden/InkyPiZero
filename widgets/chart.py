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


def _format_rain_number(v: float) -> str:
    """One decimal, trailing zero dropped - used for the rain axis's own
    top-extreme label (a real data point). See _format_rain_number_int for
    the shared temp/rain gridlines' rain value, which drops the decimal
    entirely."""
    return f"{round(v, 1):g}"


def _format_rain_number_int(v: float) -> str:
    """Rounded to a whole number, no decimal - the shared temp/rain
    gridlines' rain value (drawn at the dotted lines) is a geometric scale
    marker, not a real reading, so a decimal there added precision the
    label was never trying to convey. Per explicit user ask."""
    return str(round(v))


def _rain_gridline_labels(axis_max, grid_start, grid_end, min_temp, temp_span):
    """Computes the shared-axis rain value/label at every temp gridline
    for a candidate rain_axis_max, purely from temp values -
    plot_y0/plot_h-independent, since y_temp(v) - plot_y0 =
    (max_temp - v)/temp_span*plot_h regardless of plot_y0's absolute
    position, which simplifies render_chart's rain_at_y formula down to
    axis_max*(v - min_temp)/temp_span. Lets this run standalone during
    _choose_rain_axis_max's search (before plot_y0/plot_h even exist) and
    be reused as-is once a candidate is chosen, rather than recomputing
    with duplicated logic at draw time.

    Rounding: whole number by default; falls back to one decimal place
    (never more - per explicit user ask, no more escalating/coarsening
    tricks like earlier versions of this fallback) only for whichever
    gridline would otherwise show the exact same digits as the one just
    below it, and only when axis_max is small enough (<=9mm) that a
    decimal is meaningful - above 9mm, always whole numbers, matching the
    axis's own top-extreme (always axis_max itself, always a whole
    number). rain_at_y is monotonic in v, so a same-value collision can
    only ever involve the immediately preceding gridline - checking just
    that one catches every such run.

    collision_free only checks gridlines against EACH OTHER, deliberately
    excluding the top axis-extreme (=axis_max itself): for some temp
    shapes (grid_end very close to max_temp - little "slack" between the
    topmost real gridline and the actual high), the topmost gridline's
    value rounds to axis_max for every realistic candidate regardless of
    how far the max expands - a structural property of that shape, not
    something a bigger max can route around. render_chart's own
    "topmost_gridline_rain_label" check handles that specific case
    separately (dropping the redundant axis-extreme label), so folding it
    into this search's pass/fail would just make the search fail for that
    shape without ever finding anything better.

    Returns (labels, collision_free) - labels is [(v, rain_at_y, label),
    ...]; collision_free is True only when every gridline's own label came
    out distinct from every other gridline's."""
    labels = []
    prev_int_label = None
    seen = set()
    collision_free = True
    for v in range(grid_start, grid_end + 1, 10):
        rain_at_y = axis_max * (v - min_temp) / temp_span
        int_label = _format_rain_number_int(rain_at_y)
        if int_label == prev_int_label and axis_max <= 9:
            label = _format_rain_number(rain_at_y)
        else:
            label = int_label
        prev_int_label = int_label
        if label in seen:
            collision_free = False
        seen.add(label)
        labels.append((v, rain_at_y, label))
    return labels, collision_free


def _choose_rain_axis_max(rains, grid_start, grid_end, min_temp, temp_span):
    """Searches upward from the natural max(1, ceil(max(rains))) for a
    rain_axis_max where every gridline (using _rain_gridline_labels'
    honest whole-number/one-decimal rounding rule) produces a genuinely
    distinct label, instead of accepting the natural max's collisions and
    patching them after the fact - per explicit user ask ("expand the max
    when needed... no more rounding [tricks]"). Since rain_axis_max also
    sets the bar chart's own scale, this means the real data's peak can
    sit a little below the very top of the chart on days where expansion
    is needed, rather than always touching it - an accepted tradeoff, not
    an oversight.

    Tries a handful of steps above the natural max (per explicit user ask
    - a bounded search, not an unlimited one) before giving up and
    falling back to it; render_chart's own per-line fallback (still
    reachable via _rain_gridline_labels' rounding rule) and the
    topmost-gridline-vs-axis-extreme check remain as a safety net for
    whatever the fallback doesn't resolve, so a pathological case never
    leaves a truly unhandled collision, just possibly an accepted
    residual one - same spirit as before, just rarer now."""
    natural_max = max(1, math.ceil(max(rains, default=0)))
    for candidate in range(natural_max, natural_max + 6):
        _, collision_free = _rain_gridline_labels(candidate, grid_start, grid_end, min_temp, temp_span)
        if collision_free:
            return candidate
    return natural_max


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
    # needed early so _choose_rain_axis_max's search (below) can run
    # before plot_y0/plot_h/y_rain even exist.
    grid_start = math.ceil(min_temp / 10) * 10
    grid_end = math.floor(max_temp / 10) * 10
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
    # The expansion search (see _choose_rain_axis_max) only applies where a
    # collision is even possible: plain-number gridline labels actually
    # get drawn. Category mode's intensity words and snow/dry's absent
    # gridline numbers use the natural (real-data) max unchanged.
    if show_temp_gridlines and show_rain_gridline_labels and not show_intensity_labels:
        rain_axis_max = _choose_rain_axis_max(rains, grid_start, grid_end, min_temp, temp_span)
    else:
        rain_axis_max = max(1, math.ceil(max(rains, default=0)))
    # Precomputed once the final rain_axis_max is known, reused verbatim
    # inside the gridline-drawing loop below instead of recomputing the
    # same rounding logic there - see _rain_gridline_labels.
    rain_gridline_label_by_v = {}
    if show_temp_gridlines and show_rain_gridline_labels and not show_intensity_labels:
        _labels, _ = _rain_gridline_labels(rain_axis_max, grid_start, grid_end, min_temp, temp_span)
        rain_gridline_label_by_v = {v: label for v, _rain_at_y, label in _labels}

    band = plot_w / n
    xs = [plot_x0 + band * (i + 0.5) for i in range(n)]

    def y_temp(v):
        return plot_y0 + (max_temp - v) / temp_span * plot_h

    def y_rain(v):
        return plot_y0 + (rain_axis_max - v) / rain_axis_max * plot_h

    y_zero = y_temp(0)

    # rain bars - skip anything too small to be a meaningful bar, otherwise the
    # highlight strip alone (drawn at a fixed height) reads as a solid false
    # floor across hours with essentially no rain
    for x, rain in zip(xs, rains):
        if rain < rain_axis_max * 0.03:
            continue
        top = y_rain(rain)
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
    # The topmost interior gridline's own rain NUMBER (plain-number mode
    # only) - stays None whenever no gridlines were drawn (show_temp_gridlines
    # False) or none carry a rain label. Used below to drop the top
    # axis-extreme label specifically when it would show the exact same
    # digits as the gridline just below it - a real, reported case: a
    # near-dry day (rain_axis_max clamped to the 1mm placeholder floor) can
    # round both the axis extreme AND the topmost gridline's rain_at_y to
    # "1", and they're not close enough in *pixels* to trip the proximity
    # suppression above, so the same number visibly appeared twice.
    topmost_gridline_rain_label = None

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
        # grid_start/grid_end computed earlier, before rain_axis_max's own
        # expansion search needed them.
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

            if show_rain_gridline_labels:
                # Shared axis: temp and rain map onto the exact same
                # plot_y0..plot_y1 pixel range (two scales, one set of
                # lines - y_temp(max_temp)/y_rain(rain_axis_max) are both
                # exactly plot_y0, y_temp(min_temp)/y_rain(0) both exactly
                # plot_y1) - label the rain value at this same height
                # instead of drawing a second independent rain grid. This
                # is a geometric scale marker like the temp side, not a
                # per-hour reading - in category mode it can occasionally
                # read one band "worse" than the nearby actual-peak axis
                # label if rain_axis_max's ceil-rounding leaves enough
                # slack for an interior gridline to cross a band boundary
                # the real data never reached.
                if show_intensity_labels:
                    rain_at_y = rain_axis_max * (1 - (y - plot_y0) / plot_h)
                    rain_label = _rain_intensity_label(rain_at_y)
                else:
                    # Precomputed once for the final (possibly expanded)
                    # rain_axis_max, before this loop even started - see
                    # rain_gridline_label_by_v / _rain_gridline_labels.
                    rain_label = rain_gridline_label_by_v[v]
                draw.text((plot_x1 + 6, y), rain_label, font=font_axis, fill=PALETTE.chart_zero_line, anchor="lm")
                if not show_intensity_labels:
                    label_w = font_axis.getbbox(rain_label)[2]
                    max_rain_number_w = max(max_rain_number_w, label_w)
                    # v ascends towards grid_end each iteration, i.e. y moves
                    # towards plot_y0 (up) - the last write below always ends
                    # up holding the topmost gridline's own label once the
                    # loop finishes.
                    topmost_gridline_rain_label = rain_label
                suppress_max_rain_label = suppress_max_rain_label or near_max_rain
                suppress_min_rain_label = suppress_min_rain_label or near_min_rain
            v += 10
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
    else:
        # rain_axis_max is always a whole number (the natural max(1,
        # ceil(...)) or one of _choose_rain_axis_max's integer candidates)
        # - _format_rain_number_int makes that invariant explicit rather
        # than relying on _format_rain_number's :g formatting happening to
        # produce the same clean string for a whole-number input.
        top_label = _format_rain_number_int(rain_axis_max)
        bottom_label = "0"
    # On dry windows, rain_axis_max is always the max(1, ...) placeholder
    # floor (there's no real rain to size the axis off) - showing "1" up top
    # implies a rain reading that never happened, so it's dropped entirely
    # rather than suppressed only on gridline-collision grounds like the
    # other axis-extreme labels above. Also dropped whenever it would show
    # the exact same digits as the topmost interior gridline
    # (topmost_gridline_rain_label) - _choose_rain_axis_max's search
    # already tries to pick a rain_axis_max where this never happens (the
    # candidate's own str() is in its collision check), so this check is
    # now mostly a safety net for whenever that search exhausts its step
    # budget without finding a clean candidate and falls back to the
    # natural max - the originally reported case (a near-dry day clamped
    # to the 1mm placeholder floor, colliding with the topmost gridline
    # not close enough in *pixels* to trip suppress_max_rain_label above).
    if not suppress_max_rain_label and precip_label != "Droog" and top_label != topmost_gridline_rain_label:
        draw.text((plot_x1 + 6, y_rain(rain_axis_max)), top_label, font=font_axis, fill=text_color, anchor="lm")
        if not show_intensity_labels:
            max_rain_number_w = max(max_rain_number_w, font_axis.getbbox(top_label)[2])
    if not suppress_min_rain_label:
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
