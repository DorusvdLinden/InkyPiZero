import os
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# width / height of the source humidity_drop_filled.png / humidity_drop_empty.png
# assets (cropped from a pi4-app render - see pi_weather_display/TODO.md)
DROPLET_ASPECT = 28 / 38

# Moon glyphs (the night-clear/partly-cloudy condition icons, plus every moon
# phase) read as oversized next to the sun/cloud icons at the same box size -
# their bbox is tighter/more square, so a uniform fit-to-box scales them up
# more. Padding the cached base image (after crop, before any resize) makes
# them render smaller everywhere they're used, without a per-call-site hack.
MOON_ICON_KEYS = {
    "01n", "022n", "newmoon", "waxingcrescent", "firstquarter", "waxinggibbous",
    "fullmoon", "waninggibbous", "lastquarter", "waningcrescent",
}
MOON_FILL_FRACTION = 0.625

# humidity_drop_empty is deliberately a hollow outline (its whole purpose is
# to look "not filled" next to humidity_drop_filled) - never solidify it.
# visibility's hollow "white of the eye" between the outline and pupil is a
# real design element too (confirmed against the original InkyPi icon set),
# not a stray gap - filling it turns a recognizable eye into a blue blob.
# sunrise/sunset are a ring that's genuinely disconnected from a separate
# chevron shape below it (not a hairline crack) - no erosion radius closes
# that gap without also distorting unrelated icons; left as an outline.
NO_FILL_KEYS = {"humidity_drop_empty", "visibility", "sunrise", "sunset"}


def _fill_holes(icon: Image.Image, close_radius: int = 1) -> Image.Image:
    """Several weather-icons glyphs (the ring-style sun, the thin moon-
    crescent outline) are drawn as an outline with a transparent interior
    rather than a solid shape - against the original Flaticon-sourced icon
    set this project used to ship (see docs/attribution.md), which reads
    noticeably denser/bolder at the same pixel size. Flood-fills any
    transparent area enclosed by the icon's own opaque pixels with the
    icon's own color, leaving true (edge-connected) background transparent
    and the original antialiased edges untouched.

    The outside-reachability test (only) runs on a slightly eroded copy of
    the transparent mask, so a hairline gap from antialiasing doesn't leak
    the flood fill into what should read as an enclosed hole. Not every
    outline shape has a cleanly closeable gap this way, though - see
    NO_FILL_KEYS for icons where a bigger, genuinely disconnected opening
    (not a hairline crack) made this the wrong tool."""
    w, h = icon.size
    color = next((p[:3] for p in icon.getdata() if p[3] > 16), None)
    if color is None:
        return icon

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


def _pad_to_fraction(img: Image.Image, fraction: float) -> Image.Image:
    """Returns img centered on a larger transparent canvas so it only fills
    `fraction` of the new canvas's width/height."""
    w, h = img.size
    new_w, new_h = round(w / fraction), round(h / fraction)
    padded = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    padded.paste(img, ((new_w - w) // 2, (new_h - h) // 2), img)
    return padded


class AssetStore:
    def __init__(self, icon_dir: str, font_dir: str):
        self.icon_dir = icon_dir
        self.font_dir = font_dir
        self._icon_cache = {}
        self._resized_cache = {}
        self._font_cache = {}

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
            if key not in NO_FILL_KEYS:
                # Solidify at source resolution, before any resize - LANCZOS
                # downsampling a thin ring stroke (e.g. the sun's circle) to
                # icon-strip sizes can break it into sub-threshold-alpha
                # fragments, which then reads as several hairline gaps to
                # the flood fill and defeats it, so fill first while the
                # stroke is still solid at full size.
                img = _fill_holes(img)
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
        cache_key = (weight, size_px)
        font = self._font_cache.get(cache_key)
        if font is None:
            filename = "Jost-SemiBold.ttf" if weight == "bold" else "Jost.ttf"
            font = ImageFont.truetype(os.path.join(self.font_dir, filename), size_px)
            self._font_cache[cache_key] = font
        return font


def draw_humidity_drops(image: Image.Image, region, assets: AssetStore, filled_count: int, total: int = 5):
    """5 drops in a 3-over-2 layout, border always visible, filled up to filled_count.
    Uses pre-rendered drop images (humidity_drop_filled/empty.png) rather than
    drawing the teardrop shape - a hand-drawn polygon approximation never
    looked as clean as the original CSS/SVG-rendered shape."""
    cx, cy = region.center
    drop_h = max(1, int(region.h * 0.5))
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
