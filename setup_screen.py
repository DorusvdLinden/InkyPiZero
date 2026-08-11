"""Renders the WiFi setup screen shown on the e-paper panel whenever the
device is hosting its own access point (no known network reachable) - the
one channel guaranteed available to tell the user the AP's SSID/password
regardless of network state, since a docs page can't be read by someone
standing in front of a device with no other UI yet.

A much simpler sibling to canvas.py's WeatherCanvas - no WeatherSnapshot
dependency, no chart/gauges, just centered text."""

from PIL import Image, ImageDraw

import layout
from config import DisplayConfig
from widgets.icons import AssetStore
from widgets.palette import PALETTE


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))


def render_setup_screen(assets: AssetStore, config: DisplayConfig, ssid: str, password: str, url: str) -> Image.Image:
    # Keeps PALETTE.chart_warm/chart_cool an exact panel-palette match -
    # web_app.py is a long-running process, so without this a saturation
    # change via the settings form wouldn't reach this screen until the
    # whole service restarted (see canvas.py's WeatherCanvas for the same
    # fix on the main render path).
    PALETTE.set_saturation(config.inky_saturation)
    bg = _hex_to_rgb(config.background_color)
    text_color = _hex_to_rgb(config.text_color)
    cx = layout.CANVAS_SIZE[0] // 2

    image = Image.new("RGB", layout.CANVAS_SIZE, bg)
    draw = ImageDraw.Draw(image)

    font_heading = assets.font("bold", 34)
    font_label = assets.font("normal", 18)
    font_value = assets.font("bold", 32)
    font_footer = assets.font("normal", 15)

    y = 70
    draw.text((cx, y), "Wifi-instellingen nodig", font=font_heading, fill=text_color, anchor="ma")

    y += 90
    draw.text((cx, y), "Verbind met dit netwerk:", font=font_label, fill=text_color, anchor="ma")
    y += 26
    draw.text((cx, y), ssid, font=font_value, fill=PALETTE.chart_warm, anchor="ma")

    y += 70
    draw.text((cx, y), "Wachtwoord (hoofdlettergevoelig):", font=font_label, fill=text_color, anchor="ma")
    y += 26
    draw.text((cx, y), password, font=font_value, fill=PALETTE.chart_warm, anchor="ma")

    y += 70
    draw.text((cx, y), "Open daarna in een browser:", font=font_label, fill=text_color, anchor="ma")
    y += 26
    draw.text((cx, y), url, font=font_value, fill=PALETTE.chart_cool, anchor="ma")

    footer_y = layout.CANVAS_SIZE[1] - 40
    draw.text((cx, footer_y), "Dit scherm verdwijnt automatisch zodra de verbinding lukt.",
              font=font_footer, fill=text_color, anchor="ma")

    return layout.inset_with_margin(image, bg)
