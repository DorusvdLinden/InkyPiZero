"""Decides whether main.py should actually check for/push a render to the
physical e-paper panel on a given timer tick, or skip it - every refresh
causes a visible flash and is a real physical wear cycle, so a 10-minute
schedule shouldn't refresh unconditionally when nothing meaningfully
changed. Mirrors display_mode.py's "state file under
/var/lib/pi-weather-display/" pattern, since main.py is a one-shot job
with no memory between runs.

Two independent throttles, both configurable (config.py/the web UI):
  - should_run_check/record_check: skip a tick entirely - before even
    fetching weather data - if less than `min_interval` has passed since
    the last check attempt (config.min_update_interval_minutes).
  - should_update_display/record_display: once data's been fetched, skip
    the actual display push if the main icon/temperature are unchanged
    and less than `max_stale` has passed since the last real refresh
    (config.force_refresh_max_stale_minutes).
Both read/write the same state file - _load_state()/_write_state() do a
read-modify-write so recording one doesn't clobber the other's fields."""

import json
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

STATE_PATH = "/var/lib/pi-weather-display/display_freshness.json"
FORCE_REFRESH_PATH = "/var/lib/pi-weather-display/force_refresh_requested"


def _load_state() -> dict:
    """A missing/corrupt state file is treated as "no prior state" rather
    than crashing the render pipeline over it, matching display_mode.py/
    settings_store.py's own defensive-default convention."""
    try:
        with open(STATE_PATH) as f:
            state = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Ignoring unreadable display-freshness state %s: %s", STATE_PATH, e)
        return {}
    return state if isinstance(state, dict) else {}


def _write_state(updates: dict) -> None:
    state = _load_state()
    state.update(updates)
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp_path = f"{STATE_PATH}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(state, f)
    os.replace(tmp_path, STATE_PATH)


def should_run_check(now: datetime, min_interval: timedelta) -> bool:
    """True if it's worth even fetching weather data this tick. A
    non-positive min_interval means no extra throttling beyond the fixed
    systemd timer cadence - always True."""
    if min_interval <= timedelta(0):
        return True
    state = _load_state()
    try:
        last_check_time = datetime.fromisoformat(state["last_check_time"])
    except (KeyError, TypeError, ValueError):
        return True
    return now - last_check_time >= min_interval


def record_check(now: datetime) -> None:
    """Call once per tick that actually proceeds past should_run_check -
    whether or not it goes on to update the display."""
    _write_state({"last_check_time": now.isoformat()})


def should_update_display(icon_key: str, temp, now: datetime, max_stale: timedelta) -> bool:
    """True if the physical display should be refreshed this tick: no
    prior state (first run), the main icon or temperature changed since
    the last refresh, or max_stale has elapsed since the last refresh -
    keeps slower-changing details (forecast cards, the hourly chart, the
    "Laatste update" timestamp) from going stale indefinitely during a
    stretch of unchanged weather."""
    state = _load_state()
    if state.get("icon_key") != icon_key or state.get("temp") != temp:
        return True
    try:
        last_display_time = datetime.fromisoformat(state["last_display_time"])
    except (KeyError, TypeError, ValueError):
        return True
    return now - last_display_time >= max_stale


def record_display(icon_key: str, temp, now: datetime) -> None:
    """Call only after an actual display push - a skipped tick must not
    reset the "last displayed" reference, or the forced refresh would
    never fire during a long unchanged-weather stretch."""
    _write_state({"icon_key": icon_key, "temp": temp, "last_display_time": now.isoformat()})


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
