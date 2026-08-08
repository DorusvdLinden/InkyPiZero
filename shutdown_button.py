"""Listens for a press of the physical "A" button on the back of the Inky
Impression (GPIO5) and responds by blanking the display and shutting the Pi
down safely. Unlike main.py, this needs to run continuously in the
background rather than on a timer, since a button press can happen at any
moment - it's installed as its own persistent systemd service
(pi-weather-shutdown.service), separate from the periodic render timer."""

import logging
from datetime import timedelta
import subprocess

import gpiod
import gpiodevice
from gpiod.line import Bias, Direction, Edge
from PIL import Image

import layout
from display.inky_driver import InkyDriver

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BUTTON_A_GPIO = 5
DEBOUNCE_MS = 50


def blank_and_shutdown():
    logger.info("Button A pressed - blanking display and shutting down.")
    blank = Image.new("RGB", layout.CANVAS_SIZE, "white")
    InkyDriver().show(blank)
    subprocess.run(["poweroff"], check=True)


def main():
    chip = gpiodevice.find_chip_by_platform()
    offset = chip.line_offset_from_id(BUTTON_A_GPIO)
    request = chip.request_lines(
        consumer="pi-weather-shutdown",
        config={
            offset: gpiod.LineSettings(
                direction=Direction.INPUT,
                bias=Bias.PULL_UP,
                edge_detection=Edge.FALLING,
                debounce_period=timedelta(milliseconds=DEBOUNCE_MS),
            )
        },
    )
    logger.info("Listening for button A (GPIO%d) presses.", BUTTON_A_GPIO)
    while True:
        request.wait_edge_events()
        for _event in request.read_edge_events():
            blank_and_shutdown()
            return


if __name__ == "__main__":
    main()
