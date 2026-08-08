"""Dev-time only: converts weather-icons SVGs into the colored PNGs shipped in
assets/icons/. Not part of the running app - resvg-py is not an app
dependency, this script is run by hand when an icon needs regenerating.

Usage:
    git clone https://github.com/erikflowers/weather-icons.git ../weather-icons
    pip install resvg-py
    python scripts/generate_icons.py
"""

import io
import os
import sys

import resvg_py
from PIL import Image, ImageDraw

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
from widgets.palette import PALETTE

SVG_DIR = os.path.join(SCRIPT_DIR, "..", "..", "weather-icons", "svg")
OUT_DIR = os.path.join(SCRIPT_DIR, "..", "assets", "icons")

# "Half cloudy" icons (sun/moon peeking out from behind a cloud) - the
# source weather-icons SVGs pack the whole glyph (sun/moon rays AND cloud)
# into one single <path>, so there's no way to give the cloud a different
# color than the sun/moon via CSS the way the single-color icons above do.
# Composited here instead from two separately-colored icons: `role` picks
# which PALETTE color to render each layer in, `scale`/`dx`/`dy` position it
# on a 300x300 canvas (hand-tuned - see mock_display_output/sun_cloud_
# composite_v2.png / moon_cloud_composite_v4.png for the iterations this
# landed on).
COMPOSITE_ICONS = {
    "022d": {
        "back": ("wi-day-sunny", "sun", 0.85, 40, 0),
        "front": ("wi-cloud", "cloud", 0.78, 0, 70),
    },
    "022n": {
        "back": ("wi-night-clear", "moon", 1.15, 5, -30),
        "front": ("wi-cloud", "cloud", 0.78, 0, 70),
    },
}

# Not SVG-sourced like the icons above - two small transparent PNGs
# hand-cropped from an old pi4-app screenshot (see TODO.md), used as a
# shape/alpha template only. Their baked-in RGB was never updated to match
# the panel's actual palette, which is why they dithered almost invisible
# once the panel-matching work above made every *other* icon color exact.
HUMIDITY_DROP_FILES = ["humidity_drop_filled", "humidity_drop_empty"]


def _recolor_humidity_drops(out_dir: str):
    color = PALETTE.humidity_drop
    for name in HUMIDITY_DROP_FILES:
        template = Image.open(os.path.join(OUT_DIR, f"{name}.png")).convert("RGBA")
        alpha = template.split()[3]
        recolored = Image.new("RGBA", template.size, (*color, 0))
        recolored.putalpha(alpha)
        recolored.save(os.path.join(out_dir, f"{name}.png"))
        print(f"{name:24s} <- (recolored template)      {_hex(color)}")


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _render_svg(svg_name: str, color_hex: str, size: int = 256) -> Image.Image:
    png_bytes = resvg_py.svg_to_bytes(
        svg_path=os.path.join(SVG_DIR, f"{svg_name}.svg"), width=size, height=size,
        style_sheet=f"path {{ fill: {color_hex}; }}",
    )
    return Image.open(io.BytesIO(bytes(png_bytes))).convert("RGBA")


def _solid_silhouette(icon: Image.Image, alpha_threshold: int = 16) -> Image.Image:
    """weather-icons are drawn as hollow outlines (a ring, not a disc) - the
    icon's own path only covers the stroke, leaving the interior fully
    transparent. Returns an "L" mask that's opaque for the stroke AND any
    area it fully encloses, by flood-filling in from every corner and
    treating whatever the flood never reaches as "enclosed" rather than
    "background". Used to turn a hollow icon into a solid filled shape."""
    alpha = icon.split()[3]
    binary = alpha.point(lambda a: 255 if a > alpha_threshold else 0)
    flood = binary.copy()
    corners = [(0, 0), (flood.width - 1, 0), (0, flood.height - 1), (flood.width - 1, flood.height - 1)]
    for seed in corners:
        if flood.getpixel(seed) == 0:
            ImageDraw.floodfill(flood, seed, 128, thresh=10)
    return flood.point(lambda v: 0 if v == 128 else 255)


def _solid_fill(icon: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    """Fills icon's silhouette (stroke + any enclosed holes) with one flat
    color - e.g. turns a hollow-ring sun icon into a solid disc+rays."""
    silhouette = _solid_silhouette(icon)
    solid = Image.new("RGBA", icon.size, (*color, 255))
    solid.putalpha(silhouette)
    return solid


def _composite_icon(spec: dict, canvas_size: int = 300) -> Image.Image:
    """Composites `back` (sun/moon) behind `front` (cloud). The cloud is
    solid-filled so its opaque white interior actually occludes the part of
    the sun/moon it overlaps, rather than the sun/moon showing through a
    hollow cloud outline - see mock_display_output/sun_cloud_composite_v5.png.
    The sun/moon itself stays a hollow outline, matching the standalone
    01d/01n icons elsewhere - only the occluded portion disappears, behind
    the cloud's solid fill."""
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))

    back_svg, back_role, back_scale, back_dx, back_dy = spec["back"]
    back_color = getattr(PALETTE, back_role)
    back_render = _render_svg(back_svg, _hex(back_color))
    back_size = int(back_render.width * back_scale)
    back_resized = back_render.resize((back_size, back_size), Image.LANCZOS)
    canvas.paste(back_resized, (back_dx, back_dy), back_resized)

    front_svg, front_role, front_scale, front_dx, front_dy = spec["front"]
    front_outline_color = getattr(PALETTE, front_role)
    front_outline = _render_svg(front_svg, _hex(front_outline_color))
    front_fill = _solid_fill(front_outline, PALETTE.cloud_interior)
    front_combined = Image.alpha_composite(front_fill, front_outline)
    front_size = int(front_combined.width * front_scale)
    front_resized = front_combined.resize((front_size, front_size), Image.LANCZOS)
    canvas.paste(front_resized, (front_dx, front_dy), front_resized)

    return canvas


def _icon_map():
    """Built fresh (not at import time) so it always reflects the current
    PALETTE - matters for scripts/color_options.py, which mutates PALETTE
    in place between calls to regenerate() to preview alternatives."""
    orange, moon_yellow, cloud_blue = _hex(PALETTE.sun), _hex(PALETTE.moon), _hex(PALETTE.cloud)
    fog, storm = _hex(PALETTE.fog), _hex(PALETTE.storm)

    weather_icons = {
        "01d": ("wi-day-sunny", orange),
        "01n": ("wi-night-clear", moon_yellow),
        # 022d/022n are composited separately - see COMPOSITE_ICONS
        "02d": ("wi-day-cloudy", cloud_blue),
        "02n": ("wi-night-alt-cloudy", cloud_blue),
        "04d": ("wi-cloudy", cloud_blue),
        "50d": ("wi-day-fog", fog),
        "48d": ("wi-day-fog", fog),
        "51d": ("wi-day-sprinkle", cloud_blue),
        "53d": ("wi-day-rain", cloud_blue),
        "09d": ("wi-day-showers", cloud_blue),
        "56d": ("wi-day-sleet", cloud_blue),
        "57d": ("wi-day-sleet", cloud_blue),
        "71d": ("wi-day-snow", cloud_blue),
        "73d": ("wi-day-snow", cloud_blue),
        "13d": ("wi-day-snow-wind", cloud_blue),
        "77d": ("wi-day-snow", cloud_blue),
        "11d": ("wi-day-thunderstorm", storm),
    }
    moon_phases = {
        "newmoon": ("wi-moon-new", moon_yellow),
        "waxingcrescent": ("wi-moon-waxing-crescent-4", moon_yellow),
        "firstquarter": ("wi-moon-first-quarter", moon_yellow),
        "waxinggibbous": ("wi-moon-waxing-gibbous-4", moon_yellow),
        "fullmoon": ("wi-moon-full", moon_yellow),
        "waninggibbous": ("wi-moon-waning-gibbous-4", moon_yellow),
        "lastquarter": ("wi-moon-third-quarter", moon_yellow),
        "waningcrescent": ("wi-moon-waning-crescent-4", moon_yellow),
    }
    sun_events = {
        "sunrise": ("wi-sunrise", orange),
        "sunset": ("wi-sunset", orange),
    }
    return {**weather_icons, **moon_phases, **sun_events}


def regenerate(out_dir: str = OUT_DIR):
    if not os.path.isdir(SVG_DIR):
        raise SystemExit(
            f"weather-icons SVG dir not found at {SVG_DIR}\n"
            "Clone https://github.com/erikflowers/weather-icons.git as a sibling "
            "of this repo, or edit SVG_DIR above."
        )
    os.makedirs(out_dir, exist_ok=True)

    all_icons = _icon_map()
    for key, (svg_name, color) in all_icons.items():
        svg_path = os.path.join(SVG_DIR, f"{svg_name}.svg")
        png_bytes = resvg_py.svg_to_bytes(
            svg_path=svg_path, width=256, height=256,
            style_sheet=f"path {{ fill: {color}; }}",
        )
        out_path = os.path.join(out_dir, f"{key}.png")
        with open(out_path, "wb") as f:
            f.write(bytes(png_bytes))
        print(f"{key:8s} <- {svg_name:30s} {color}")

    for key, spec in COMPOSITE_ICONS.items():
        icon = _composite_icon(spec)
        icon.save(os.path.join(out_dir, f"{key}.png"))
        back_name, front_name = spec["back"][0], spec["front"][0]
        print(f"{key:8s} <- composite: {back_name} + {front_name}")

    _recolor_humidity_drops(out_dir)
    total = len(all_icons) + len(COMPOSITE_ICONS) + len(HUMIDITY_DROP_FILES)
    print(f"\n{total} icons written to {out_dir}")


if __name__ == "__main__":
    regenerate()
