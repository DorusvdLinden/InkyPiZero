"""Entry point for the standalone weather renderer. Designed to be invoked
once per refresh by a systemd timer (or, for local testing, run directly) -
no Flask app, no playlist/plugin machinery, just fetch -> render -> display."""

import argparse
import logging
import os
from datetime import datetime

from config import DisplayConfig
from weather_data import fetch_snapshot, WeatherSnapshot
from canvas import WeatherCanvas
from widgets.icons import AssetStore
import display_freshness
import display_mode
import settings_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(BASE_DIR, "assets", "icons")
FONT_DIR = os.path.join(BASE_DIR, "assets", "fonts")


def render_canvas(config: DisplayConfig, data: WeatherSnapshot, screen_mode: str | None = None,
                   compact_style: str = "icon_left"):
    assets = AssetStore(ICON_DIR, FONT_DIR)
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

    config = settings_store.load_config()

    # --mock-output is for local preview/testing - always render, skip the
    # real-hardware-only "don't refresh unless something changed" check.
    if args.mock_output:
        logger.info("Fetching weather data")
        data = fetch_snapshot(config)
        image = render_canvas(config, data, screen_mode=args.screen_mode, compact_style=args.compact_style)
        from display.mock_driver import MockDriver
        MockDriver(args.mock_output).show(image)
        return

    forced = display_freshness.consume_forced_refresh()
    logger.info("Fetching weather data")
    data = fetch_snapshot(config)
    now = datetime.now()
    if not forced and not display_freshness.should_update_display(data.current_icon_key, data.current_temp, now):
        logger.info("Skipping display update - icon/temp unchanged and last refresh was under an hour ago")
        return

    image = render_canvas(config, data, screen_mode=args.screen_mode, compact_style=args.compact_style)
    from display.inky_driver import InkyDriver
    InkyDriver(saturation=config.inky_saturation).show(image)
    display_freshness.record_display(data.current_icon_key, data.current_temp, now)


if __name__ == "__main__":
    main()
