"""Static temperature/rain chart, replacing the Chart.js line+bar chart in
weather.html. Draws directly into the target region of the main canvas
(unlike the gauge widgets, this one doesn't need its own scratch image since
there's no rotation/scaling involved)."""

import math
from PIL import Image, ImageDraw

from widgets.icons import thicken_icon
from widgets.palette import PALETTE

LEFT_MARGIN = 46  # fits a wide axis label with its unit suffix ("-36°C")
RIGHT_MARGIN = 42
TOP_MARGIN = 12
BOTTOM_MARGIN = 44
ICON_SIZE = 30


def _decimal_point_center_x(label: str, font) -> float | None:
    """x-offset (from the label's own left edge) to the horizontal center
    of its "." character, or None if the label has no decimal point (e.g.
    a whole-number rain value like "1 mm")."""
    dot_idx = label.find(".")
    if dot_idx == -1:
        return None
    before = font.getbbox(label[:dot_idx])[2] if dot_idx > 0 else 0
    upto = font.getbbox(label[:dot_idx + 1])[2]
    return (before + upto) / 2


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


def render_chart(image: Image.Image, region, hourly, sun_events, text_color, icon_lookup,
                  graph_icon_step, font_small, font_bold, unit_label_temp, unit_label_rain):
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
    rain_axis_max = max(1, math.ceil(max(rains, default=0) * 10) / 10)

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
        x = plot_x0
        while x < plot_x1:
            draw.line([(x, y), (min(x + 5, plot_x1), y)], fill=color, width=2)
            x += 9
        label_dy = 14 if (plot_y1 - y) > 20 else -14
        label = f"{value}°" if unit_label_temp != "K" else str(value)
        draw.text((plot_x0 + plot_w / 2, y + label_dy), label, font=font_bold, fill=color, anchor="mm")

    # black dashed 0deg reference line, only shown when the day actually
    # dips below freezing (min_temp < 0 means actual_min < 0 too, since
    # min_temp = min(actual_min, 0)) - without this there'd be no marker
    # at all for where freezing sits once the axis itself is clamped to
    # the actual (negative) low instead of 0.
    if min_temp < 0:
        x = plot_x0
        while x < plot_x1:
            draw.line([(x, y_zero), (min(x + 5, plot_x1), y_zero)], fill=PALETTE.chart_zero_line, width=2)
            x += 9
        label_dy = 14 if (plot_y1 - y_zero) > 20 else -14
        draw.text((plot_x0 + plot_w / 2, y_zero + label_dy), "0°", font=font_bold, fill=PALETTE.chart_zero_line, anchor="mm")

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
    temp_unit_suffix = unit_label_temp if unit_label_temp == "K" else f"°{unit_label_temp}"
    rain_max_label = f"{rain_axis_max:g}"
    draw.text((plot_x0 - 6, y_temp(max_temp)), f"{max_temp}{temp_unit_suffix}", font=font_bold, fill=text_color, anchor="rm")
    draw.text((plot_x0 - 6, y_temp(min_temp)), f"{min_temp}{temp_unit_suffix}", font=font_bold, fill=text_color, anchor="rm")
    draw.text((plot_x1 + 6, y_rain(rain_axis_max)), rain_max_label, font=font_bold, fill=text_color, anchor="lm")
    draw.text((plot_x1 + 6, y_rain(0)), "0", font=font_bold, fill=text_color, anchor="lm")

    # "Regen [mm]" is centered on the decimal point of the rain-axis-max
    # number (e.g. the "." in "4.5") when it has one, so the two read as
    # visually aligned rather than the label just trailing off to the
    # right of it. Whole numbers ("1"/"0") have no "." to align to, so
    # fall back to a flat 2mm (~10px) gap off the axis line.
    regen_label = f"Regen [{unit_label_rain}]"
    regen_bbox = font_bold.getbbox(regen_label)
    regen_rotated_w = (regen_bbox[3] - regen_bbox[1]) + 2
    dot_offset = _decimal_point_center_x(rain_max_label, font_bold)
    if dot_offset is not None:
        regen_x = plot_x1 + 6 + dot_offset - regen_rotated_w / 2
    else:
        regen_x = plot_x1 + 10
    _vertical_text(image, (regen_x, (plot_y0 + plot_y1) // 2), regen_label, font_bold, text_color)

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
