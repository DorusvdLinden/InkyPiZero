"""Static temperature/rain chart, replacing the Chart.js line+bar chart in
weather.html. Draws directly into the target region of the main canvas
(unlike the gauge widgets, this one doesn't need its own scratch image since
there's no rotation/scaling involved)."""

import math
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ORANGE = (230, 81, 0)
BLUE = (13, 71, 161)
FILL_YELLOW = (252, 204, 5)

LEFT_MARGIN = 34
RIGHT_MARGIN = 42
TOP_MARGIN = 12
BOTTOM_MARGIN = 34
ICON_SIZE = 20
MOON_ICON_SIZE = 14
MOON_ICON_KEYS = {"01n", "022n"}


def _darken(icon: Image.Image, factor: float = 0.5) -> Image.Image:
    """Darkens an RGBA icon's color while preserving its alpha channel - makes
    the small chart-strip icons read as bolder/higher-contrast against the
    pale background than the shared full-brightness asset colors."""
    r, g, b, a = icon.split()
    scale = lambda band: band.point(lambda v: int(v * factor))
    return Image.merge("RGBA", (scale(r), scale(g), scale(b), a))


def _fill_holes(icon: Image.Image, close_radius: int = 1) -> Image.Image:
    """Some weather-icons glyphs (the ring-style sun, the thin moon-crescent
    outline, the sunrise/sunset ring-with-a-horizon-gap) are drawn as an
    outline with a transparent interior rather than a solid shape - fine at
    the larger sizes used elsewhere, but reads as faint and hard to see at
    the chart strip's small ICON_SIZE. Flood-fills any transparent area
    enclosed by the icon's own opaque pixels with the icon's own color,
    leaving true (edge-connected) background transparent and the original
    antialiased edges untouched.

    The outside-reachability test (only) is run on a slightly eroded copy of
    the transparent mask, so a hairline gap in an otherwise-closed outline -
    like the horizon notch in the sunrise/sunset glyph - doesn't leak the
    flood fill into what should read as an enclosed hole."""
    w, h = icon.size
    color = next((p[:3] for p in icon.getdata() if p[3] > 16), (0, 0, 0))

    is_transparent = icon.split()[3].point(lambda a: 255 if a <= 16 else 0)
    closed = is_transparent
    for _ in range(close_radius):
        closed = closed.filter(ImageFilter.MinFilter(3))

    padded = Image.new("L", (w + 2, h + 2), 255)
    padded.paste(closed, (1, 1))
    ImageDraw.floodfill(padded, (0, 0), 128)
    flooded = padded.crop((1, 1, w + 1, h + 1))
    reached_bg = flooded.point(lambda v: 255 if v == 128 else 0)
    hole_mask = ImageChops.subtract(is_transparent, reached_bg)

    filled = icon.copy()
    patch = Image.new("RGBA", (w, h), (*color, 255))
    filled.paste(patch, (0, 0), hole_mask)
    return filled


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
        draw.rectangle([x - w / 2, top, x + w / 2, plot_y1], fill=(*BLUE, 130))
        draw.rectangle([x - w / 2, top, x + w / 2, min(top + 3, plot_y1)], fill=(*BLUE, 230))

    # temperature fill (between the curve and the 0 degree line) - drawn on a
    # separate RGBA layer and alpha-composited in, since ImageDraw on the
    # main RGB image silently drops the alpha byte and renders fully opaque
    curve = [(x, y_temp(t)) for x, t in zip(xs, temps)]
    fill_poly = curve + [(xs[-1], y_zero), (xs[0], y_zero)]
    fill_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(fill_layer).polygon(fill_poly, fill=(*FILL_YELLOW, 90))
    image.paste(fill_layer, (0, 0), fill_layer)

    # temperature line, colored per segment by sign
    for (x1, y1), (x2, y2), t1, t2 in zip(curve, curve[1:], temps, temps[1:]):
        color = ORANGE if (t1 + t2) >= 0 else BLUE
        draw.line([(x1, y1), (x2, y2)], fill=color, width=4, joint="curve")

    # actual min/max labels (no reference line - just the value at its height)
    for value, label_dy, color in [(actual_max, -14, ORANGE if actual_max >= 0 else BLUE),
                                    (actual_min, 4, ORANGE if actual_min >= 0 else BLUE)]:
        y = y_temp(value)
        label = f"{value}°" if unit_label_temp != "K" else str(value)
        draw.text((plot_x0 + plot_w / 2, y + label_dy), label, font=font_bold, fill=color, anchor="mm")

    # axes
    draw.line([(plot_x0, plot_y0), (plot_x0, plot_y1)], fill=text_color, width=2)
    draw.line([(plot_x1, plot_y0), (plot_x1, plot_y1)], fill=text_color, width=2)
    draw.line([(plot_x0, plot_y1), (plot_x1, plot_y1)], fill=text_color, width=2)

    draw.text((plot_x0 - 6, y_temp(max_temp)), f"{max_temp}°", font=font_bold, fill=text_color, anchor="rm")
    draw.text((plot_x0 - 6, y_temp(min_temp)), f"{min_temp}°", font=font_bold, fill=text_color, anchor="rm")
    draw.text((plot_x1 + 6, y_rain(rain_axis_max)), f"{rain_axis_max:g} {unit_label_rain}", font=font_bold, fill=text_color, anchor="lm")
    draw.text((plot_x1 + 6, y_rain(0)), f"0 {unit_label_rain}", font=font_bold, fill=text_color, anchor="lm")

    _vertical_text(image, (region.x + 4, (plot_y0 + plot_y1) // 2), unit_label_temp, font_bold, text_color)
    _vertical_text(image, (region.right - 16, (plot_y0 + plot_y1) // 2), "Regen", font_bold, text_color)

    # x-axis hour labels - same cadence as the icon strip below, so each
    # icon sits directly under its hour's label instead of drifting out of
    # sync with a differently-stepped label grid
    for i in range(0, n, graph_icon_step):
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
        size = MOON_ICON_SIZE if icon_key in MOON_ICON_KEYS else ICON_SIZE
        icon = icon_lookup(icon_key, (size, size))
        if icon:
            icon = _fill_holes(_darken(icon))
            px = int(xs[i] - size / 2)
            py = icon_y + (ICON_SIZE - size) // 2
            image.paste(icon, (px, py), icon)
