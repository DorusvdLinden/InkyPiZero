"""Entry point for the standalone weather renderer. Designed to be invoked
once per refresh by a systemd timer (or, for local testing, run directly) -
no Flask app, no playlist/plugin machinery, just fetch -> render -> display."""

import argparse
import logging
import os

from config import DisplayConfig
from weather_data import fetch_snapshot
from canvas import WeatherCanvas
from widgets.icons import AssetStore
import display_mode

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(BASE_DIR, "assets", "icons")
FONT_DIR = os.path.join(BASE_DIR, "assets", "fonts")


def render(config: DisplayConfig, screen_mode: str | None = None, compact_style: str = "icon_left"):
    assets = AssetStore(ICON_DIR, FONT_DIR)
    logger.info("Fetching weather data")
    data = fetch_snapshot(config)
    logger.info("Rendering canvas")
    if screen_mode is None:
        screen_mode = display_mode.get_mode()
    return WeatherCanvas(assets, config, screen_mode, compact_style).render(data)


def main():
    parser = argparse.ArgumentParser(description="Render and display the current weather snapshot.")
    parser.add_argument("--mock-output", help="Save the render to this file instead of driving a real Inky display.")
    parser.add_argument("--screen-mode", choices=sorted(display_mode.VALID_MODES),
                         help="Override the button-selected screen mode (for local testing).")
    parser.add_argument("--compact-style", choices=["icon_left", "icon_above", "icon_above_row"],
                         default="icon_left", help="Which 'compact' mode mockup style to use (for local testing).")
    args = parser.parse_args()

    config = DisplayConfig()
    image = render(config, screen_mode=args.screen_mode, compact_style=args.compact_style)

    if args.mock_output:
        from display.mock_driver import MockDriver
        MockDriver(args.mock_output).show(image)
    else:
        from display.inky_driver import InkyDriver
        InkyDriver(saturation=config.inky_saturation).show(image)


if __name__ == "__main__":
    main()
