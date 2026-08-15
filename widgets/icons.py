import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# width / height of the source humidity_drop_filled.png / humidity_drop_empty.png
# assets (cropped from a pi4-app render - see pi_weather_display/TODO.md)
DROPLET_ASPECT = 28 / 38

ICON_THICKEN_PX = 1
ICON_THICKEN_STRENGTH = 0.5  # 0 = original thin lines, 1 = full 1px dilation


def thicken_icon(icon: Image.Image, amount: int = ICON_THICKEN_PX,
                  strength: float = ICON_THICKEN_STRENGTH) -> Image.Image:
    """Dilates the icon's alpha channel to make thin strokes (the sun's
    ring, cloud outlines, etc.) read as bolder at small sizes, without
    filling any enclosed interior - a ring stays a ring, just a thicker
    one.

    Multi-color aware: two-tone composite icons (e.g. "022d"'s orange sun
    behind a blue cloud, see generate_icons.py) get each color's own alpha
    dilated independently and re-stacked, rather than flattening the whole
    icon to one sampled color - colors are composited back in the order
    they first appear scanning top-to-bottom, which for these composites
    happens to match their original front/back layering (the foreground
    layer's pixels start lower in the icon, so its color always ends up
    composited last/on top).

    A full 1px dilation (strength=1) reads a bit heavier than wanted, and
    MaxFilter only supports whole-pixel steps, so `strength` blends
    between the original and dilated alpha to land in between."""
    pixels = list(icon.getdata())
    # Only near-fully-opaque pixels count as "a color" - low-alpha
    # antialiased edge pixels can carry a contaminated/darkened RGB (e.g. a
    # bright yellow's edge sampling as dark olive), which would otherwise
    # get used to fill in the newly-thickened border, visibly discoloring
    # the icon.
    colors = list(dict.fromkeys(p[:3] for p in pixels if p[3] > 200))
    if not colors:
        color = next((p[:3] for p in pixels if p[3] > 16), None)
        colors = [color] if color else []
    if not colors:
        return icon

    result = Image.new("RGBA", icon.size, (0, 0, 0, 0))
    for color in colors:
        mask = Image.new("L", icon.size)
        mask.putdata([p[3] if p[:3] == color else 0 for p in pixels])
        dilated = mask.filter(ImageFilter.MaxFilter(amount * 2 + 1))
        thickened_mask = Image.blend(mask, dilated, strength)
        layer = Image.new("RGBA", icon.size, (*color, 0))
        layer.putalpha(thickened_mask)
        result = Image.alpha_composite(result, layer)
    return result

# Moon glyphs (the night-clear condition icon, plus every moon phase) read as
# oversized next to the sun/cloud icons at the same box size - their bbox is
# tighter/more square, so a uniform fit-to-box scales them up more. Padding
# the cached base image (after crop, before any resize) makes them render
# smaller everywhere they're used, without a per-call-site hack. Doesn't
# include "022n" - that's a moon+cloud composite (see generate_icons.py),
# already cloud-icon-proportioned like "04d", not tightly-cropped like a bare
# moon.
MOON_ICON_KEYS = {
    "01n", "newmoon", "waxingcrescent", "firstquarter", "waxinggibbous",
    "fullmoon", "waninggibbous", "lastquarter", "waningcrescent",
}
MOON_FILL_FRACTION = 0.625


def _pad_to_fraction(img: Image.Image, fraction: float) -> Image.Image:
    """Returns img centered on a larger transparent canvas so it only fills
    `fraction` of the new canvas's width/height."""
    w, h = img.size
    new_w, new_h = round(w / fraction), round(h / fraction)
    padded = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    padded.paste(img, ((new_w - w) // 2, (new_h - h) // 2), img)
    return padded


# One entry per selectable font family (config.font_family / the web UI) -
# "normal"/"bold" filenames, both loaded the same way via .font(). Bitter
# ships as a single variable-weight file (no separate bold TTF) - its
# named "Bold"/"Regular" instances are selected in .font() below via
# set_variation_by_name(), confirmed to exist via font.get_variation_names().
FONT_FAMILIES = {
    "jost": {"normal": "Jost.ttf", "bold": "Jost-SemiBold.ttf"},
    "bitter": {"normal": "Bitter-Variable.ttf", "bold": "Bitter-Variable.ttf"},
}
BITTER_VARIATIONS = {"normal": "Regular", "bold": "Bold"}

# Neither Jost nor Bitter has non-Latin glyphs (Cyrillic aside, for Jost) -
# a location name that comes back from Nominatim in e.g. Japanese/Chinese
# renders as a blank gap otherwise (Pillow's single-TTF loader does no
# automatic per-character font substitution the way a browser would).
# Noto Sans JP was picked over a narrower "just CJK" or "just Cyrillic"
# font for its unusually broad combined coverage (Source Han Sans-based -
# full CJK Unified Ideographs, Hiragana/Katakana, extensive Latin,
# Cyrillic, Greek, and more in one file) - see draw_text_with_fallback().
# Complex-script languages (Arabic, Thai, Devanagari-based, Hebrew) would
# still render with correct *glyphs* but wrong shaping/ordering, since
# Pillow's text() has no bidi/shaping engine - a real but separate
# limitation from missing glyphs, not solved here.
FALLBACK_FONT_FILE = "NotoSansJP-Variable.ttf"
FALLBACK_FONT_VARIATIONS = {"normal": "Regular", "bold": "Bold"}
# A private-use-area codepoint no real font legitimately maps - probing a
# font with it reveals its shared .notdef glyph's bbox "fingerprint" (see
# _has_glyph). PIL/FreeType have no direct "does this font have glyph X"
# API; comparing against this reliably infers it without adding a cmap-
# parsing dependency (fontTools isn't installed in this repo).
_NOTDEF_PROBE_CHAR = ""


class AssetStore:
    def __init__(self, icon_dir: str, font_dir: str, font_family: str = "jost"):
        self.icon_dir = icon_dir
        self.font_dir = font_dir
        self.font_family = font_family
        self._icon_cache = {}
        self._resized_cache = {}
        self._font_cache = {}
        self._fallback_font_cache = {}
        self._notdef_bbox_cache = {}

    def icon(self, key: str, size: tuple[int, int] | None = None) -> Image.Image | None:
        img = self._icon_cache.get(key)
        if img is None:
            path = os.path.join(self.icon_dir, f"{key}.png")
            if not os.path.exists(path):
                return None
            raw = Image.open(path).convert("RGBA")
            # Source PNGs carry wildly inconsistent transparent padding (some
            # fill their whole 512x512 canvas, some leave >20% margin) -
            # cropping to actual content first is what makes a uniform resize
            # below produce consistent-looking icons instead of some reading
            # bigger/smaller or off-center than others.
            bbox = raw.getbbox()
            img = raw.crop(bbox) if bbox else raw
            if key in MOON_ICON_KEYS:
                img = _pad_to_fraction(img, MOON_FILL_FRACTION)
            self._icon_cache[key] = img
        if size is None:
            return img
        cache_key = (key, size)
        resized = self._resized_cache.get(cache_key)
        if resized is None:
            target_w, target_h = size
            scale = min(target_w / img.width, target_h / img.height)
            fit_w, fit_h = max(1, round(img.width * scale)), max(1, round(img.height * scale))
            fitted = img.resize((fit_w, fit_h), Image.LANCZOS)
            resized = Image.new("RGBA", size, (0, 0, 0, 0))
            resized.paste(fitted, ((target_w - fit_w) // 2, (target_h - fit_h) // 2), fitted)
            self._resized_cache[cache_key] = resized
        return resized

    def font(self, weight: str, size_px: int) -> ImageFont.FreeTypeFont:
        cache_key = (self.font_family, weight, size_px)
        font = self._font_cache.get(cache_key)
        if font is None:
            filename = FONT_FAMILIES[self.font_family][weight]
            font = ImageFont.truetype(os.path.join(self.font_dir, filename), size_px)
            if self.font_family == "bitter":
                font.set_variation_by_name(BITTER_VARIATIONS[weight])
            self._font_cache[cache_key] = font
        return font

    def fallback_font(self, weight: str, size_px: int) -> ImageFont.FreeTypeFont:
        """Noto Sans JP, for characters `.font()`'s active family can't
        render - see FALLBACK_FONT_FILE's module docstring comment."""
        cache_key = (weight, size_px)
        font = self._fallback_font_cache.get(cache_key)
        if font is None:
            font = ImageFont.truetype(os.path.join(self.font_dir, FALLBACK_FONT_FILE), size_px)
            font.set_variation_by_name(FALLBACK_FONT_VARIATIONS[weight])
            self._fallback_font_cache[cache_key] = font
        return font

    def _has_glyph(self, font: ImageFont.FreeTypeFont, char: str) -> bool:
        """True if `font` has a real glyph for `char`, not its shared
        .notdef fallback glyph - see _NOTDEF_PROBE_CHAR's module docstring
        comment for how/why this works without a cmap-parsing dependency.
        `font`'s notdef bbox is computed once and cached (keyed by the
        font object itself - both AssetStore's own font caches already
        guarantee one object per distinct family/weight/size)."""
        notdef_bbox = self._notdef_bbox_cache.get(id(font))
        if notdef_bbox is None:
            notdef_bbox = font.getbbox(_NOTDEF_PROBE_CHAR)
            self._notdef_bbox_cache[id(font)] = notdef_bbox
        if char.isspace():
            return True
        return font.getbbox(char) != notdef_bbox

    def draw_text_with_fallback(self, draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str,
                                 weight: str, size_px: int, fill, anchor: str = "la"):
        """Like `draw.text()`, but characters `.font()`'s active family
        can't render (e.g. a Japanese/Chinese location name under Jost or
        Bitter, neither of which has CJK glyphs) fall back to Noto Sans JP
        instead of silently vanishing - see FALLBACK_FONT_FILE. Draws run
        by run (consecutive characters sharing the same font) rather than
        character by character, so each script's own glyph spacing/
        kerning stays natural instead of every character getting isolated
        advance widths.

        Only left-anchored anchors ("l*") are supported - mixed-font text
        can't be centered/right-aligned without rendering once already to
        measure its total width, and every real call site left-aligns."""
        if not anchor.startswith("l"):
            raise ValueError(f"draw_text_with_fallback only supports left anchors, got {anchor!r}")
        primary = self.font(weight, size_px)
        fallback = self.fallback_font(weight, size_px)

        runs = []
        for char in text:
            use_fallback = not self._has_glyph(primary, char)
            if runs and runs[-1][0] == use_fallback:
                runs[-1] = (use_fallback, runs[-1][1] + char)
            else:
                runs.append((use_fallback, char))

        x, y = xy
        for use_fallback, run in runs:
            font = fallback if use_fallback else primary
            draw.text((x, y), run, font=font, fill=fill, anchor=anchor)
            x += font.getlength(run)


def draw_humidity_drops(image: Image.Image, region, assets: AssetStore, filled_count: int, total: int = 5):
    """5 drops in a 3-over-2 layout, border always visible, filled up to filled_count.
    Uses pre-rendered drop images (humidity_drop_filled/empty.png) rather than
    drawing the teardrop shape - a hand-drawn polygon approximation never
    looked as clean as the original CSS/SVG-rendered shape."""
    cx, cy = region.center
    drop_h = max(1, int(region.h * 0.42))
    drop_w = max(1, int(drop_h * DROPLET_ASPECT))
    spacing = drop_w

    filled_icon = assets.icon("humidity_drop_filled", (drop_w, drop_h))
    empty_icon = assets.icon("humidity_drop_empty", (drop_w, drop_h))

    row1_y = cy - region.h * 0.16
    row2_y = cy + region.h * 0.22

    def row_positions(count, y):
        start_x = cx - spacing * (count - 1) / 2
        return [(start_x + i * spacing, y) for i in range(count)]

    positions = row_positions(3, row1_y) + row_positions(2, row2_y)
    for i, (x, y) in enumerate(positions):
        icon = filled_icon if i < filled_count else empty_icon
        if icon:
            image.paste(icon, (int(x - drop_w / 2), int(y - drop_h / 2)), icon)
