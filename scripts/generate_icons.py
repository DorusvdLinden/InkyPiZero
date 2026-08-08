"""Dev-time only: converts weather-icons SVGs into the colored PNGs shipped in
assets/icons/. Not part of the running app - resvg-py is not an app
dependency, this script is run by hand when an icon needs regenerating.

Usage:
    git clone https://github.com/erikflowers/weather-icons.git ../weather-icons
    pip install resvg-py
    python scripts/generate_icons.py
"""

import os
import sys

import resvg_py
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
from widgets.palette import PALETTE

SVG_DIR = os.path.join(SCRIPT_DIR, "..", "..", "weather-icons", "svg")
OUT_DIR = os.path.join(SCRIPT_DIR, "..", "assets", "icons")

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


def _icon_map():
    """Built fresh (not at import time) so it always reflects the current
    PALETTE - matters for scripts/color_options.py, which mutates PALETTE
    in place between calls to regenerate() to preview alternatives."""
    orange, moon_yellow, cloud_blue = _hex(PALETTE.sun), _hex(PALETTE.moon), _hex(PALETTE.cloud)
    fog, storm = _hex(PALETTE.fog), _hex(PALETTE.storm)

    weather_icons = {
        "01d": ("wi-day-sunny", orange),
        "01n": ("wi-night-clear", moon_yellow),
        "022d": ("wi-day-sunny-overcast", orange),
        "022n": ("wi-night-alt-partly-cloudy", moon_yellow),
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

    _recolor_humidity_drops(out_dir)
    print(f"\n{len(all_icons) + len(HUMIDITY_DROP_FILES)} icons written to {out_dir}")


if __name__ == "__main__":
    regenerate()
