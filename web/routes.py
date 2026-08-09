"""Routes for the always-on settings/WiFi-management web UI (and the WiFi
setup flow when the device is hosting its own AP) - see
docs/networking.md for the network-mode architecture this sits on top of."""

import dataclasses
import logging
import subprocess

from flask import Blueprint, flash, redirect, render_template, request, url_for

import settings_store
import wifi_manager
from config import DisplayConfig

logger = logging.getLogger(__name__)

bp = Blueprint("web", __name__)


def _trigger_rerender():
    """Reuses the exact precedent button_listener.py's switch_mode() already
    established - a settings save should show up within seconds, not wait
    for the next scheduled timer tick. Best-effort: local dev machines
    (no systemd) just log and move on rather than failing the request."""
    try:
        subprocess.run(["systemctl", "start", "pi-weather-display.service"], check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        logger.warning("Could not trigger an immediate re-render: %s", e)


def _config_from_form(form) -> tuple[DisplayConfig, list[str]]:
    """Parses submitted settings-form fields into a DisplayConfig on top of
    the currently-saved config. A field that fails to parse/validate keeps
    its current value and adds an error message instead of the whole
    submission being silently discarded."""
    current = settings_store.load_config()
    values = dataclasses.asdict(current)
    errors = []

    def _set(name, parser):
        raw = form.get(name)
        try:
            value = parser(raw)
        except (TypeError, ValueError):
            errors.append(f"Ongeldige waarde voor {name}: {raw!r}")
            return
        if not settings_store.FIELD_VALIDATORS[name](value):
            errors.append(f"Ongeldige waarde voor {name}: {raw!r}")
            return
        values[name] = value

    _set("latitude", float)
    _set("longitude", float)
    _set("units", str)
    _set("timezone", str)
    _set("time_format", str)
    _set("forecast_days", int)
    _set("graph_icon_step", int)
    values["show_moon_phase"] = form.get("show_moon_phase") == "on"
    _set("background_color", str)
    _set("text_color", str)
    _set("inky_saturation", float)
    _set("refresh_interval_seconds", int)

    return DisplayConfig(**values), errors


@bp.route("/")
def index():
    mode = wifi_manager.current_mode()
    return render_template("index.html", mode=mode, screen_mode=_current_screen_mode())


def _current_screen_mode() -> str:
    import display_mode
    return display_mode.get_mode()


@bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        config, errors = _config_from_form(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("settings.html", config=config), 400
        settings_store.save_config(config)
        _trigger_rerender()
        flash("Instellingen opgeslagen.", "success")
        return redirect(url_for("web.settings"))

    config = settings_store.load_config()
    return render_template("settings.html", config=config)
