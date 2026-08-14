from PIL import ImageDraw

from widgets.icons import thicken_icon


def _fit_font(assets, text: str, max_size: int, max_width: float, min_size: int = 8):
    """Shrinks in 2px steps until text fits max_width, floor min_size - same
    shrink-to-fit approach as WeatherCanvas._fit_font (canvas.py), needed
    here too since the mm-rain text's width is unbounded (a 2-digit "12mm"
    vs. a decimal "0.6mm") while narrower forecast_days settings shrink the
    card itself, so a fixed font size can overflow the card at high
    forecast_days."""
    for size in range(max_size, min_size - 1, -2):
        font = assets.font("normal", size)
        if font.getlength(text) <= max_width:
            return font
    return assets.font("normal", min_size)


def draw_forecast_card(image, region, day, assets, text_color, show_moon: bool):
    draw = ImageDraw.Draw(image)
    # day.quality_border_color is already a resolved RGB tuple (see
    # weather_data._quality_tier_and_color) - user-editable via
    # weather_quality.toml, nothing left to look up here.
    draw.rounded_rectangle(
        [region.x, region.y, region.right - 1, region.bottom - 1],
        radius=8, outline=day.quality_border_color, width=3,
    )

    icon_size = int(min(region.w * 0.85, region.h * 0.45))
    icon = assets.icon(day.icon_key, (icon_size, icon_size))
    cx = region.center[0]
    top_y = region.y + 6

    mm_text = mm_font = None
    mm_gap = 3
    icon_x = cx - icon_size // 2
    if day.rain_expected:
        # Never round to "0mm" for a day that's flagged as expecting rain -
        # anything under 1mm keeps a decimal instead.
        candidate_text = f"{day.precip_mm:.1f}mm" if day.precip_mm < 1 else f"{round(day.precip_mm)}mm"
        # Shrink to fit the remaining card width (narrow cards at high
        # forecast_days). No artificial floor on the available width - if
        # even _fit_font's smallest size still doesn't genuinely fit,
        # skip the text entirely (icon stays centered, as on a dry day)
        # rather than let it overflow past the border.
        available_width = max(region.w - icon_size - mm_gap - 4, 1)
        candidate_font = _fit_font(assets, candidate_text, 12, available_width)
        if candidate_font.getlength(candidate_text) <= available_width:
            mm_text, mm_font = candidate_text, candidate_font
            mm_width = mm_font.getlength(mm_text)
            icon_x = int(cx - (icon_size + mm_gap + mm_width) / 2)

    if icon:
        icon = thicken_icon(icon)
        image.paste(icon, (icon_x, top_y), icon)

    if mm_text:
        draw.text((icon_x + icon_size + mm_gap, top_y + icon_size // 2), mm_text,
                   font=mm_font, fill=text_color, anchor="lm")

    temps_y = top_y + icon_size + 4
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
