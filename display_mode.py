"""Tracks which screen layout is currently selected via the physical B/C/D
buttons on the back of the Inky Impression - persisted to a small state
file since main.py runs as a one-shot timer job, not a long-running
process, so it can't just hold the choice in memory between renders.
button_listener.py writes this when a button is pressed; main.py reads it
on every render."""

import os

STATE_PATH = "/var/lib/pi-weather-display/screen_mode"

DEFAULT_MODE = "original"
VALID_MODES = {"original", "gridlines"}


def get_mode() -> str:
    try:
        with open(STATE_PATH) as f:
            mode = f.read().strip()
    except FileNotFoundError:
        return DEFAULT_MODE
    return mode if mode in VALID_MODES else DEFAULT_MODE


def set_mode(mode: str):
    if mode not in VALID_MODES:
        raise ValueError(f"Unknown screen mode: {mode!r}")
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        f.write(mode)
