"""Renders the WiFi setup screen shown on the e-paper panel whenever the
device is hosting its own access point (no known network reachable) - the
one channel guaranteed available to tell the user the AP's SSID/password
regardless of network state, since a docs page can't be read by someone
standing in front of a device with no other UI yet.

A much simpler sibling to canvas.py's WeatherCanvas - no WeatherSnapshot
dependency, no chart/gauges, just centered text."""

import qrcode
from PIL import Image, ImageDraw

import layout
from config import DisplayConfig
from widgets.icons import AssetStore
from widgets.palette import PALETTE


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))


def _wifi_qr_payload(ssid: str, password: str) -> str:
    """The standard `WIFI:` URI scheme a phone's native camera app
    recognizes for one-tap network joining, instead of a plain URL.
    Escapes the four characters the spec reserves (backslash itself,
    then `;`/`,`/`:`) - not actually reachable with this app's own
    generated SSID/password (wifi_manager.AP_SSID_PREFIX + a hex MAC
    suffix; AP_PASSWORD_CHARS is alphanumeric-only), but a saved
    station-network SSID a user typed in by hand could contain any of
    them, and this function has no way to know which case it's called
    for."""
    def esc(s: str) -> str:
        for ch in ("\\", ";", ",", ":"):
            s = s.replace(ch, f"\\{ch}")
        return s
    return f"WIFI:S:{esc(ssid)};T:WPA;P:{esc(password)};;"


def _wifi_qr_image(ssid: str, password: str, box_size: int = 6) -> Image.Image:
    qr = qrcode.QRCode(border=2, box_size=box_size)
    qr.add_data(_wifi_qr_payload(ssid, password))
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


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

    draw.text((cx, 40), "Wifi-instellingen nodig", font=font_heading, fill=text_color, anchor="ma")

    # Two columns below the heading: text instructions (left, for anyone
    # typing it in by hand) and a scannable WIFI: QR code (right, for a
    # one-tap phone camera join) - neither replaces the other, since a
    # QR code alone isn't readable/verifiable by eye and plain text alone
    # means typing a random-generated password by hand.
    left_cx = layout.CANVAS_SIZE[0] // 4
    y = 150
    draw.text((left_cx, y), "Verbind met dit netwerk:", font=font_label, fill=text_color, anchor="ma")
    y += 26
    draw.text((left_cx, y), ssid, font=font_value, fill=PALETTE.chart_warm, anchor="ma")

    y += 70
    draw.text((left_cx, y), "Wachtwoord (hoofdlettergevoelig):", font=font_label, fill=text_color, anchor="ma")
    y += 26
    draw.text((left_cx, y), password, font=font_value, fill=PALETTE.chart_warm, anchor="ma")

    y += 70
    draw.text((left_cx, y), "Open daarna in een browser:", font=font_label, fill=text_color, anchor="ma")
    y += 26
    draw.text((left_cx, y), url, font=font_value, fill=PALETTE.chart_cool, anchor="ma")

    right_cx = layout.CANVAS_SIZE[0] * 3 // 4
    qr_img = _wifi_qr_image(ssid, password)
    qr_x = right_cx - qr_img.width // 2
    qr_y = 160
    image.paste(qr_img, (qr_x, qr_y))
    draw.text((right_cx, qr_y + qr_img.height + 16), "Of scan deze QR-code om direct te verbinden",
              font=font_label, fill=text_color, anchor="ma")

    footer_y = layout.CANVAS_SIZE[1] - 40
    draw.text((cx, footer_y), "Dit scherm verdwijnt automatisch zodra de verbinding lukt.",
              font=font_footer, fill=text_color, anchor="ma")

    return layout.inset_with_margin(image, bg)
