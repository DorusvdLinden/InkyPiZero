"""Decides whether main.py should actually push a render to the physical
e-paper panel on a given timer tick, or skip it - every refresh causes a
visible flash and is a real physical wear cycle, so a 10-minute schedule
shouldn't refresh unconditionally when nothing meaningfully changed.
Mirrors display_mode.py's "state file under /var/lib/pi-weather-display/"
pattern, since main.py is a one-shot job with no memory between runs."""

import json
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

STATE_PATH = "/var/lib/pi-weather-display/display_freshness.json"
FORCE_REFRESH_PATH = "/var/lib/pi-weather-display/force_refresh_requested"

MAX_STALE = timedelta(hours=1)


def should_update_display(icon_key: str, temp, now: datetime) -> bool:
    """True if the physical display should be refreshed this tick: no
    prior state (first run), the main icon or temperature changed since
    the last refresh, or MAX_STALE has elapsed since the last refresh -
    keeps slower-changing details (forecast cards, the hourly chart, the
    "Laatste update" timestamp) from going stale indefinitely during a
    stretch of unchanged weather. A missing/corrupt state file is treated
    as "no prior state" rather than crashing the render pipeline over it,
    matching display_mode.py/settings_store.py's own defensive-default
    convention."""
    try:
        with open(STATE_PATH) as f:
            state = json.load(f)
    except FileNotFoundError:
        return True
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Ignoring unreadable display-freshness state %s: %s", STATE_PATH, e)
        return True

    if not isinstance(state, dict) or state.get("icon_key") != icon_key or state.get("temp") != temp:
        return True
    try:
        last_display_time = datetime.fromisoformat(state["last_display_time"])
    except (KeyError, TypeError, ValueError):
        return True
    return now - last_display_time >= MAX_STALE


def record_display(icon_key: str, temp, now: datetime) -> None:
    """Call only after an actual display push - a skipped tick must not
    reset the "last displayed" reference, or the hourly force would never
    fire during a long unchanged-weather stretch."""
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp_path = f"{STATE_PATH}.tmp"
    with open(tmp_path, "w") as f:
        json.dump({"icon_key": icon_key, "temp": temp, "last_display_time": now.isoformat()}, f)
    os.replace(tmp_path, STATE_PATH)


def request_forced_refresh() -> None:
    """Called by button_listener.py/web/routes.py right before they force
    an immediate re-render - a user-triggered change (screen mode button,
    settings save) must always show up, not be silently skipped because
    the icon/temp happen to be unchanged."""
    os.makedirs(os.path.dirname(FORCE_REFRESH_PATH), exist_ok=True)
    with open(FORCE_REFRESH_PATH, "w"):
        pass


def consume_forced_refresh() -> bool:
    """True (and clears the sentinel) if a forced refresh was requested
    since the last render."""
    try:
        os.remove(FORCE_REFRESH_PATH)
        return True
    except FileNotFoundError:
        return False
