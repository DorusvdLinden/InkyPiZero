"""Dev-time only: converts weather-icons SVGs into the colored PNGs shipped in
assets/icons/. Not part of the running app - resvg-py is not an app
dependency, this script is run by hand when an icon needs regenerating.

Usage:
    git clone https://github.com/erikflowers/weather-icons.git ../weather-icons
    pip install resvg-py
    python scripts/generate_icons.py
"""

import os

import resvg_py

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SVG_DIR = os.path.join(SCRIPT_DIR, "..", "..", "weather-icons", "svg")
OUT_DIR = os.path.join(SCRIPT_DIR, "..", "assets", "icons")

ORANGE = "#ff8c00"       # sun - Pimoroni ACeP-native orange
MOON_YELLOW = "#ffff00"  # moon - Pimoroni ACeP-native yellow
CLOUD_BLUE = "#0000ff"   # plain cloud, rain cloud, and snow cloud all share this - ACeP-native blue
FOG = "#000000"          # no native gray on the panel - flat black avoids dithering
STORM = "#000000"

# icon_key -> (weather-icons svg name, fill color)
WEATHER_ICONS = {
    "01d": ("wi-day-sunny", ORANGE),
    "01n": ("wi-night-clear", MOON_YELLOW),
    "022d": ("wi-day-sunny-overcast", ORANGE),
    "022n": ("wi-night-alt-partly-cloudy", MOON_YELLOW),
    "02d": ("wi-day-cloudy", CLOUD_BLUE),
    "02n": ("wi-night-alt-cloudy", CLOUD_BLUE),
    "04d": ("wi-cloudy", CLOUD_BLUE),
    "50d": ("wi-day-fog", FOG),
    "48d": ("wi-day-fog", FOG),
    "51d": ("wi-day-sprinkle", CLOUD_BLUE),
    "53d": ("wi-day-rain", CLOUD_BLUE),
    "09d": ("wi-day-showers", CLOUD_BLUE),
    "56d": ("wi-day-sleet", CLOUD_BLUE),
    "57d": ("wi-day-sleet", CLOUD_BLUE),
    "71d": ("wi-day-snow", CLOUD_BLUE),
    "73d": ("wi-day-snow", CLOUD_BLUE),
    "13d": ("wi-day-snow-wind", CLOUD_BLUE),
    "77d": ("wi-day-snow", CLOUD_BLUE),
    "11d": ("wi-day-thunderstorm", STORM),
}

MOON_PHASES = {
    "newmoon": ("wi-moon-new", MOON_YELLOW),
    "waxingcrescent": ("wi-moon-waxing-crescent-4", MOON_YELLOW),
    "firstquarter": ("wi-moon-first-quarter", MOON_YELLOW),
    "waxinggibbous": ("wi-moon-waxing-gibbous-4", MOON_YELLOW),
    "fullmoon": ("wi-moon-full", MOON_YELLOW),
    "waninggibbous": ("wi-moon-waning-gibbous-4", MOON_YELLOW),
    "lastquarter": ("wi-moon-third-quarter", MOON_YELLOW),
    "waningcrescent": ("wi-moon-waning-crescent-4", MOON_YELLOW),
}

SUN_EVENTS = {
    "sunrise": ("wi-sunrise", ORANGE),
    "sunset": ("wi-sunset", ORANGE),
}

ALL_ICONS = {**WEATHER_ICONS, **MOON_PHASES, **SUN_EVENTS}


def main():
    if not os.path.isdir(SVG_DIR):
        raise SystemExit(
            f"weather-icons SVG dir not found at {SVG_DIR}\n"
            "Clone https://github.com/erikflowers/weather-icons.git as a sibling "
            "of this repo, or edit SVG_DIR above."
        )

    for key, (svg_name, color) in ALL_ICONS.items():
        svg_path = os.path.join(SVG_DIR, f"{svg_name}.svg")
        png_bytes = resvg_py.svg_to_bytes(
            svg_path=svg_path, width=256, height=256,
            style_sheet=f"path {{ fill: {color}; }}",
        )
        out_path = os.path.join(OUT_DIR, f"{key}.png")
        with open(out_path, "wb") as f:
            f.write(bytes(png_bytes))
        print(f"{key:8s} <- {svg_name:30s} {color}")

    print(f"\n{len(ALL_ICONS)} icons written to {OUT_DIR}")


if __name__ == "__main__":
    main()
