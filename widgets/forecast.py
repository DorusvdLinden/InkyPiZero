from PIL import ImageDraw

from widgets.icons import thicken_icon
from widgets.palette import PALETTE


def _fit_stacked_lines(assets, top_text: str, bottom_text: str, max_size: int, max_width: float,
                        block_center_y: int, block_bottom_limit: float, min_size: int = 8):
    """Shrinks in 2px steps (same shrink-to-fit approach as
    WeatherCanvas._fit_font in canvas.py) until a font size satisfies
    width AND height together, returning (font, top_line_y, line_h,
    block_width) for the caller to draw at directly - or None if no size
    in range satisfies both.

    Width and height are checked *jointly* per candidate size, not
    width-then-height sequentially: a smaller size that would satisfy both
    must not be skipped just because a larger size already happened to
    satisfy width alone. Since both `line_h` and the horizontal fit only
    get smaller/easier as size decreases, the first size (largest) that
    passes both checks is the best available. Centers the two-line block
    vertically at `block_center_y`, and only accepts a size whose block
    bottom stays at or above `block_bottom_limit` (e.g. the row of text
    below it)."""
    for size in range(max_size, min_size - 1, -2):
        font = assets.font("normal", size)
        top_width, bottom_width = font.getlength(top_text), font.getlength(bottom_text)
        if top_width > max_width or bottom_width > max_width:
            continue
        line_h = font.size + 1
        top_line_y = block_center_y - line_h // 2
        if top_line_y + 2 * line_h <= block_bottom_limit:
            return font, top_line_y, line_h, max(top_width, bottom_width)
    return None


def draw_forecast_card(image, region, day, assets, text_color, show_moon: bool):
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        [region.x, region.y, region.right - 1, region.bottom - 1],
        radius=8, outline=PALETTE.card_border, width=2,
    )

    icon_size = int(min(region.w * 0.85, region.h * 0.45))
    icon = assets.icon(day.icon_key, (icon_size, icon_size))
    cx = region.center[0]
    top_y = region.y + 6

    temps_y = top_y + icon_size + 4

    mm_number = mm_font = mm_top_y = mm_line_h = mm_width = None
    mm_unit = "mm"
    mm_gap = 3
    icon_x = cx - icon_size // 2
    if day.rain_expected:
        # Never round to "0mm" for a day that's flagged as expecting rain -
        # anything under 1mm keeps a decimal instead.
        candidate_number = f"{day.precip_mm:.1f}" if day.precip_mm < 1 else f"{round(day.precip_mm)}"
        # Shrink to fit the remaining card width (narrow cards at high
        # forecast_days) AND the two-line block's height above temps_y -
        # checked jointly per candidate size (see _fit_stacked_lines) so a
        # smaller size satisfying both isn't skipped just because a larger
        # one already passed the width check alone. No artificial floor on
        # the available width - if no size in range satisfies both, skip
        # the text entirely (icon stays centered, as on a dry day) rather
        # than ever drawing something that overflows the card or collides
        # with the day-label row below it.
        available_width = max(region.w - icon_size - mm_gap - 4, 1)
        fit = _fit_stacked_lines(assets, candidate_number, mm_unit, 12, available_width,
                                  block_center_y=top_y + icon_size // 2, block_bottom_limit=temps_y)
        if fit:
            mm_font, mm_top_y, mm_line_h, mm_width = fit
            mm_number = candidate_number
            icon_x = int(cx - (icon_size + mm_gap + mm_width) / 2)

    if icon:
        icon = thicken_icon(icon)
        image.paste(icon, (icon_x, top_y), icon)

    if mm_number:
        text_x = icon_x + icon_size + mm_gap
        draw.text((text_x, mm_top_y), mm_number, font=mm_font, fill=text_color, anchor="lm")
        draw.text((text_x, mm_top_y + mm_line_h), mm_unit, font=mm_font, fill=text_color, anchor="lm")

    font_bold = assets.font("bold", max(10, int(region.w * 0.15)))
    draw.text((cx, temps_y), day.day_label, font=font_bold, fill=text_color, anchor="ma")
    draw.text((cx, temps_y + font_bold.size + 1), f"{day.high}° / {day.low}°", font=font_bold, fill=text_color, anchor="ma")

    if show_moon:
        moon_size = 14
        moon_y = region.bottom - moon_size - 4
        moon_icon = assets.icon(day.moon_icon_key, (moon_size, moon_size))
        if moon_icon:
            moon_icon = thicken_icon(moon_icon)
            image.paste(moon_icon, (region.x + 6, moon_y), moon_icon)
        draw.text((region.x + 6 + moon_size + 4, moon_y + moon_size // 2), f"{day.moon_phase_pct}%",
                   font=assets.font("normal", 11), fill=text_color, anchor="lm")
