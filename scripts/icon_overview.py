"""Dev-time only: renders a contact-sheet overview of every icon in
assets/icons/, each labeled with its filename (the icon_key used
throughout the app) - a quick visual reference for the full icon set,
not part of the running app.

Usage:
    python scripts/icon_overview.py
"""

import os
import sys

from PIL import Image, ImageDraw

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.join(SCRIPT_DIR, "..")
sys.path.insert(0, REPO_DIR)

from widgets.icons import AssetStore  # noqa: E402

ICON_DIR = os.path.join(REPO_DIR, "assets", "icons")
FONT_DIR = os.path.join(REPO_DIR, "assets", "fonts")
OUT_PATH = os.path.join(REPO_DIR, "mock_display_output", "icon_overviews", "full_icon_set_white_bg.png")

BACKGROUND = (255, 255, 255)  # matches config.DisplayConfig.background_color
TEXT_COLOR = (0, 0, 0)

COLUMNS = 6
CELL_W = 108
CELL_H = 92
ICON_BOX = 48
PADDING = 12

# Preferred ordering: the auto-generated weather/moon/sun set in the same
# order scripts/generate_icons.py defines them, then any other icon assets
# (humidity drops, visibility) that aren't part of that generated set.
PREFERRED_ORDER = [
    "01d", "01n", "022d", "022n", "02d", "02n", "04d", "50d", "48d",
    "51d", "53d", "09d", "56d", "57d", "71d", "73d", "13d", "77d", "11d",
    "newmoon", "waxingcrescent", "firstquarter", "waxinggibbous", "fullmoon",
    "waninggibbous", "lastquarter", "waningcrescent",
    "sunrise", "sunset",
]


def main():
    all_keys = {os.path.splitext(f)[0] for f in os.listdir(ICON_DIR) if f.endswith(".png")}
    ordered = [k for k in PREFERRED_ORDER if k in all_keys]
    extra = sorted(all_keys - set(ordered))
    keys = ordered + extra

    assets = AssetStore(ICON_DIR, FONT_DIR)
    font = assets.font("normal", 11)

    rows = -(-len(keys) // COLUMNS)  # ceil
    width = COLUMNS * CELL_W + PADDING * 2
    height = rows * CELL_H + PADDING * 2

    sheet = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)

    for i, key in enumerate(keys):
        col, row = i % COLUMNS, i // COLUMNS
        cx = PADDING + col * CELL_W + CELL_W // 2
        top = PADDING + row * CELL_H

        icon = assets.icon(key, (ICON_BOX, ICON_BOX))
        if icon:
            sheet.paste(icon, (cx - ICON_BOX // 2, top), icon)
        draw.text((cx, top + ICON_BOX + 6), key, font=font, fill=TEXT_COLOR, anchor="ma")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    sheet.save(OUT_PATH)
    print(f"{len(keys)} icons -> {OUT_PATH}")


if __name__ == "__main__":
    main()
