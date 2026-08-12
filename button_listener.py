"""Listens for presses of the physical buttons on the back of the Inky
Impression and responds accordingly:
  - Button A blanks the display and shuts the Pi down.
  - Button B switches to the "original" screen layout.
  - Button C switches to the "gridlines" screen layout (10deg reference
    grid instead of the day's actual min/max lines) - the default.
  - Button D switches to the "compact" screen layout (4 details instead
    of 6).
B/C/D all trigger an immediate re-render so the new layout shows right
away, rather than waiting for the next scheduled timer tick.

Unlike main.py, this needs to run continuously in the background rather
than on a timer, since a button press can happen at any moment - it's
installed as its own persistent systemd service (pi-weather-buttons.service),
separate from the periodic render timer.

GPIO pin numbers follow Pimoroni's standard 4-button layout for the Inky
Impression (A=5, B=6, C=16, D=24) - all four individually confirmed via a
live probe/press on the real board."""

import logging
from datetime import timedelta
import subprocess

import gpiod
import gpiodevice
from gpiod.line import Bias, Direction, Edge
from PIL import Image

import layout
import display_freshness
import display_mode
import settings_store
from display.inky_driver import InkyDriver

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BUTTON_GPIO = {"A": 5, "B": 6, "C": 16, "D": 24}
DEBOUNCE_MS = 50


def blank_and_shutdown():
    logger.info("Button A pressed - blanking display and shutting down.")
    blank = Image.new("RGB", layout.CANVAS_SIZE, "white")
    saturation = settings_store.load_config().inky_saturation
    InkyDriver(saturation=saturation).show(blank)
    subprocess.run(["poweroff"], check=True)


def switch_mode(mode: str):
    logger.info("Switching to %r screen mode.", mode)
    display_mode.set_mode(mode)
    display_freshness.request_forced_refresh()
    subprocess.run(["systemctl", "start", "pi-weather-display.service"], check=True)


def main():
    chip = gpiodevice.find_chip_by_platform()
    offsets = {label: chip.line_offset_from_id(gpio) for label, gpio in BUTTON_GPIO.items()}
    offset_to_label = {offset: label for label, offset in offsets.items()}
    request = chip.request_lines(
        consumer="pi-weather-buttons",
        config={
            offset: gpiod.LineSettings(
                direction=Direction.INPUT,
                bias=Bias.PULL_UP,
                edge_detection=Edge.FALLING,
                debounce_period=timedelta(milliseconds=DEBOUNCE_MS),
            )
            for offset in offsets.values()
        },
    )
    logger.info("Listening for button presses: %s.", BUTTON_GPIO)
    while True:
        request.wait_edge_events()
        for event in request.read_edge_events():
            label = offset_to_label.get(event.line_offset)
            if label == "A":
                blank_and_shutdown()
                return
            elif label == "B":
                switch_mode("original")
            elif label == "C":
                switch_mode("gridlines")
            elif label == "D":
                switch_mode("compact")


if __name__ == "__main__":
    main()
