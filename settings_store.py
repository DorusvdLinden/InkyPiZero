"""Persists user-editable settings as a JSON overlay on top of
DisplayConfig's dataclass defaults - `main.py` otherwise only ever
constructs a fresh DisplayConfig() from source. Mirrors display_mode.py's
"state file under /var/lib/pi-weather-display/" pattern, scaled from one
string to the full settings schema.

Validation happens two different ways on purpose: load_config() is lenient
(a missing/invalid field just falls back to that field's own dataclass
default - a corrupt or half-written settings file must never take the
render pipeline down with it), while save_config() is strict (rejects the
whole write with every problem listed at once, so a bad web-form submission
never reaches disk)."""

import dataclasses
import json
import logging
import os
import re

from config import DisplayConfig
from widgets.icons import FONT_FAMILIES

logger = logging.getLogger(__name__)

STATE_PATH = "/var/lib/pi-weather-display/settings.json"

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _valid_time_format(v):
    return v in ("24h", "12h")


def _valid_hex_color(v):
    return isinstance(v, str) and bool(_HEX_COLOR_RE.match(v))


def _valid_latitude(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and -90 <= v <= 90


def _valid_longitude(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and -180 <= v <= 180


def _valid_saturation(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and 0.0 <= v <= 1.0


def _valid_positive_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def _valid_nonnegative_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _valid_bool(v):
    return isinstance(v, bool)


def _valid_timezone(v):
    return isinstance(v, str) and len(v) > 0


def _valid_font_family(v):
    return v in FONT_FAMILIES


# One validator per DisplayConfig field - keep in sync with config.py.
FIELD_VALIDATORS = {
    "latitude": _valid_latitude,
    "longitude": _valid_longitude,
    "timezone": _valid_timezone,
    "time_format": _valid_time_format,
    "forecast_days": _valid_positive_int,
    "graph_icon_step": _valid_positive_int,
    "show_moon_phase": _valid_bool,
    "background_color": _valid_hex_color,
    "text_color": _valid_hex_color,
    "inky_saturation": _valid_saturation,
    "font_family": _valid_font_family,
    "min_update_interval_minutes": _valid_nonnegative_int,
    "force_refresh_max_stale_minutes": _valid_positive_int,
}


def load_config() -> DisplayConfig:
    """Reads STATE_PATH if present and overlays every field that validates
    on top of DisplayConfig()'s own defaults - missing, invalid, or
    unreadable data silently falls back to the default instead of ever
    crashing the render pipeline."""
    defaults = DisplayConfig()
    try:
        with open(STATE_PATH) as f:
            raw = json.load(f)
    except FileNotFoundError:
        return defaults
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Ignoring unreadable settings file %s: %s", STATE_PATH, e)
        return defaults

    if not isinstance(raw, dict):
        logger.warning("Ignoring settings file %s: not a JSON object", STATE_PATH)
        return defaults

    overrides = {}
    for field_name, validator in FIELD_VALIDATORS.items():
        if field_name not in raw:
            continue
        value = raw[field_name]
        if validator(value):
            overrides[field_name] = value
        else:
            logger.warning("Ignoring invalid saved value for %r: %r", field_name, value)
    return dataclasses.replace(defaults, **overrides)


def save_config(config: DisplayConfig) -> None:
    """Validates every field first - raises ValueError listing every
    problem at once if any fail - then writes atomically (temp file +
    os.replace()) so a reader never sees a torn/partial file. No file lock:
    writes are rare (a human submitting a form) and atomic replace already
    rules out a torn read."""
    data = dataclasses.asdict(config)
    errors = [f"{name}={data[name]!r}" for name, validator in FIELD_VALIDATORS.items() if not validator(data[name])]
    if errors:
        raise ValueError(f"Invalid settings: {', '.join(errors)}")

    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp_path = f"{STATE_PATH}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, STATE_PATH)
