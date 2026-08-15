from PIL import ImageDraw

from widgets.icons import thicken_icon
from widgets.palette import PALETTE


def _fit_stacked_lines(assets, top_text: str, bottom_text: str, max_size: int, max_width: float,
                        block_center_y: int, block_bottom_limit: float, min_size: int = 8, margin: int = 1):
    """Shrinks in 1px steps until a font size satisfies width AND height
    together, returning (font, top_line_y, line_h, block_width) for the
    caller to draw at directly - or None if no size in range satisfies
    both. Bold weight (the only weight this is used for).

    1px steps rather than WeatherCanvas._fit_font's 2px (canvas.py) -
    `max_size` here is derived from card width and can land on either
    parity, unlike that function's callers, which always pass an even
    `max_size`; stepping by 2 from an odd `max_size` would skip `min_size`
    entirely and could report "doesn't fit" even when `min_size` itself
    would have worked.

    Width and height are checked *jointly* per candidate size, not
    width-then-height sequentially: a smaller size that would satisfy both
    must not be skipped just because a larger size already happened to
    satisfy width alone. Since both `line_h` and the horizontal fit only
    get smaller/easier as size decreases, the first size (largest) that
    passes both checks is the best available. Centers the two-line block
    vertically at `block_center_y`, and only accepts a size whose block
    bottom stays at least `margin` px above `block_bottom_limit` (e.g. the
    row of text below it) - not literally flush/touching. `margin` is
    small (not the several-px gap `_fit_font`-style helpers elsewhere in
    this file use) because the natural gap at the default forecast_days=7
    is itself only ~1px (line_h's `font.size + 1` is an approximation, not
    exact glyph metrics) - a bigger default here would shrink the mm-rain
    text below the day-label/temps size at the *default* setting, working
    against the whole point of sharing that size in the first place.

    The block's true bottom edge (not just an upper bound guess) matters
    here: both lines are drawn with `anchor="lm"` (each line's own y is
    its *vertical center*, not its top) at `top_line_y` and
    `top_line_y + line_h` - so line 1 spans
    `[top_line_y - line_h/2, top_line_y + line_h/2]` and line 2 spans
    `[top_line_y + line_h/2, top_line_y + 1.5*line_h]`. The block's real
    bottom edge is `top_line_y + 1.5*line_h`, not `top_line_y + 2*line_h`
    - using the latter (as an earlier version of this function did) is
    off by half a line height and needlessly rejects sizes that would
    have rendered fine."""
    # The height check can never pass above ~23px regardless of font size
    # (pinned to icon_size, see draw_forecast_card), but callers can pass
    # a much larger max_size (bold_size is width-derived, unbounded).
    # Capping the loop's start avoids dozens of pointless iterations at a
    # low forecast_days, every rainy card, every render, on Pi Zero W
    # hardware (docs/changes.md entry 38) - 32 chosen for real headroom
    # above that observed ceiling, not just barely above it.
    start_size = min(max_size, 32)
    for size in range(start_size, min_size - 1, -1):
        font = assets.font("bold", size)  # cached per (weight, size) on AssetStore, shared across cards/render
        # Height depends only on `size` (not on the text), so it's cheap
        # integer arithmetic - check it first and skip the two getlength()
        # glyph-shaping calls entirely for a size that could never pass.
        line_h = font.size + 1
        top_line_y = block_center_y - line_h // 2
        block_bottom = top_line_y + line_h + line_h // 2  # line 2's own bottom edge, see docstring
        if block_bottom > block_bottom_limit - margin:
            continue
        top_width = font.getlength(top_text)
        if top_width > max_width:
            continue
        bottom_width = font.getlength(bottom_text)
        if bottom_width <= max_width:
            return font, top_line_y, line_h, max(top_width, bottom_width)
    return None


def draw_forecast_card(image, region, day, assets, text_color, show_moon: bool):
    draw = ImageDraw.Draw(image)
    # Plain black border - the weather-quality classification pipeline
    # (weather_data.py: weather_quality.toml, _load_weather_quality_config,
    # _band_tier, _quality_tier_and_color, DayForecast.quality_border_color)
    # is deliberately kept and still computed every render; this card just
    # doesn't consume the resolved color for its border, at the user's
    # request, for a different use later.
    draw.rounded_rectangle(
        [region.x, region.y, region.right - 1, region.bottom - 1],
        radius=8, outline=PALETTE.card_border, width=2,
    )

    icon_size = int(min(region.w * 0.85, region.h * 0.45))
    icon = assets.icon(day.icon_key, (icon_size, icon_size))
    cx = region.center[0]
    top_y = region.y + 6

    temps_y = top_y + icon_size + 4
    # Shared with the mm-rain text below (one source of truth for "the
    # card's bold text size") rather than each computing its own copy of
    # this formula - the user's explicit ask was to match the mm-rain
    # (and day-code, already matching) style to the day-label/temps size.
    # Only a guaranteed exact match when the mm-rain text doesn't need to
    # shrink - see the comment where it's used below.
    bold_size = max(10, int(region.w * 0.15))

    mm_number = None  # mm_font/mm_top_y/mm_line_h are only read below when this is set
    mm_unit = "mm"
    mm_gap = 3
    icon_x = cx - icon_size // 2
    if day.rain_expected:
        # Never round to "0mm" for a day that's flagged as expecting rain -
        # anything under 1mm keeps a decimal instead.
        candidate_number = f"{day.precip_mm:.1f}" if day.precip_mm < 1 else f"{round(day.precip_mm)}"
        # Same bold size as the day-label/temps text below when it fits,
        # shrunk below it otherwise - checked jointly for width (narrow
        # cards at high forecast_days) AND height (the two-line block's
        # height above temps_y) per candidate size (see
        # _fit_stacked_lines) so a smaller size satisfying both isn't
        # skipped just because a larger one already passed the width check
        # alone. No artificial floor on the available width - if no size
        # in range satisfies both, skip the text entirely (icon stays
        # centered, as on a dry day) rather than ever drawing something
        # that overflows the card or collides with the day-label row below
        # it. bold_size is only an exact size match at forecast_days 5-10
        # (see docs/settings.md) - below 5, icon_size caps out
        # independently of card width while bold_size keeps growing, so
        # the vertical budget above temps_y stops growing with it and
        # this shrinks below bold_size well before running out of
        # available_width; above 10, available_width itself becomes the
        # binding constraint instead (see TODO.md).
        available_width = max(region.w - icon_size - mm_gap - 4, 1)
        fit = _fit_stacked_lines(assets, candidate_number, mm_unit, bold_size, available_width,
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

    font_bold = assets.font("bold", bold_size)
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
