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
    """One decimal, trailing zero dropped - shared by every plain-mm rain
    label (axis extremes and gridline values) so they read consistently."""
    return f"{round(v, 1):g}"


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
                  graph_icon_step, font_small, font_bold, font_axis, unit_label_temp, precip_label,
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
    rain_axis_max = max(1, math.ceil(max(rains, default=0)))
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

    # Set True below only when show_temp_gridlines mode actually draws at
    # least one gridline label - read further down to decide whether the
    # vertical precip side-label should stand in for it.
    any_gridline_labeled = False

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
        grid_start = math.ceil(min_temp / 10) * 10
        grid_end = math.floor(max_temp / 10) * 10
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
                any_gridline_labeled = True
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
                rain_at_y = rain_axis_max * (1 - (y - plot_y0) / plot_h)
                rain_label = _rain_intensity_label(rain_at_y) if show_intensity_labels else _format_rain_number(rain_at_y)
                draw.text((plot_x1 + 6, y), rain_label, font=font_axis, fill=PALETTE.chart_zero_line, anchor="lm")
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
        top_label = _format_rain_number(rain_axis_max)
        bottom_label = "0"
    if not suppress_max_rain_label:
        draw.text((plot_x1 + 6, y_rain(rain_axis_max)), top_label, font=font_axis, fill=text_color, anchor="lm")
    if not suppress_min_rain_label:
        draw.text((plot_x1 + 6, y_rain(0)), bottom_label, font=font_axis, fill=text_color, anchor="lm")

    # The precipitation label ("Regen [mm]" / "Hagel [mm]" / "Sneeuw [cm]" /
    # "Droog" - picked in weather_data.py based on the hourly window's actual
    # weather codes) sits a flat 2mm (~10px) gap off the axis line - no
    # decimal-point alignment to worry about, since the numbers above it
    # (rain_axis_max, always a whole number) and the intensity-band words
    # both have no decimal point to align to. In intensity-label mode the
    # "[mm]" unit suffix is dropped - it's no longer accurate once the axis
    # isn't showing millimeters. Dropped whenever a rain/hail gridline
    # label was actually drawn (any_gridline_labeled, only ever set True
    # when show_rain_gridline_labels - see above) - its rotated span
    # (~90px of a ~104px-tall plot, vertically centered) collided with the
    # shared gridlines' rain-value labels, which communicate the rain
    # scale without it. Snow/dry never set any_gridline_labeled (their
    # gridline numbers have no self-explanatory unit/word the way rain's
    # do), so their side label always shows, same as before this feature.
    # (Every gridline label now always draws regardless of proximity to the
    # axis extremes, and v=0 - hence at least one gridline - is always in
    # range since min_temp <= 0 <= max_temp, so any_gridline_labeled is
    # unconditionally True whenever show_rain_gridline_labels is True.)
    if not (show_temp_gridlines and any_gridline_labeled):
        side_label = precip_label.removesuffix(" [mm]") if show_intensity_labels else precip_label
        regen_x = plot_x1 + 10
        _vertical_text(image, (regen_x, (plot_y0 + plot_y1) // 2), side_label, font_bold, text_color)

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
