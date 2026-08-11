"""Routes for the always-on settings/WiFi-management web UI (and the WiFi
setup flow when the device is hosting its own AP) - see
docs/networking.md for the network-mode architecture this sits on top of."""

import dataclasses
import logging
import subprocess

from flask import Blueprint, flash, redirect, render_template, request, url_for

import display_freshness
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
    display_freshness.request_forced_refresh()
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
    _set("timezone", str)
    _set("time_format", str)
    _set("forecast_days", int)
    _set("graph_icon_step", int)
    values["show_moon_phase"] = form.get("show_moon_phase") == "on"
    _set("background_color", str)
    _set("text_color", str)
    _set("inky_saturation", float)
    _set("min_update_interval_minutes", int)
    _set("force_refresh_max_stale_minutes", int)

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


@bp.route("/wifi")
def wifi():
    return render_template(
        "wifi.html",
        mode=wifi_manager.current_mode(),
        networks=wifi_manager.list_networks(),
    )


@bp.route("/wifi/add", methods=["POST"])
def wifi_add():
    ssid = request.form.get("ssid", "").strip()
    password = request.form.get("password", "")
    if not ssid:
        flash("SSID mag niet leeg zijn.", "error")
        return redirect(url_for("web.wifi"))

    try:
        wifi_manager.add_network(ssid, password or None)
    except (ValueError, RuntimeError) as e:
        flash(f"Netwerk toevoegen mislukt: {e}", "error")
        return redirect(url_for("web.wifi"))

    # "Continue button resets networking and retries" - only meaningful if
    # we were stranded in AP mode to begin with; an already-connected user
    # adding a second network for later shouldn't get disconnected for it.
    if wifi_manager.current_mode() == "ap":
        if wifi_manager.connect(ssid):
            flash(f"Verbonden met {ssid}.", "success")
        else:
            wifi_manager.ensure_ap_mode()
            flash(f"Verbinden met {ssid} is mislukt - controleer het wachtwoord en probeer opnieuw. "
                  f"Het netwerk is wel opgeslagen; je kan het hieronder bewerken.", "error")
    else:
        flash(f"Netwerk {ssid} opgeslagen.", "success")
    return redirect(url_for("web.wifi"))


@bp.route("/wifi/<profile>/edit", methods=["POST"])
def wifi_edit(profile):
    password = request.form.get("password", "")
    try:
        wifi_manager.edit_network(profile, password)
    except (ValueError, RuntimeError) as e:
        flash(f"Bijwerken mislukt: {e}", "error")
        return redirect(url_for("web.wifi"))

    is_active = any(n["name"] == profile and n["active"] for n in wifi_manager.list_networks())
    if is_active:
        # re-authenticate immediately with the new password rather than
        # waiting for the router to eventually reject the stale one
        if wifi_manager.connect(profile):
            flash(f"{profile} bijgewerkt en opnieuw verbonden.", "success")
        else:
            flash(f"{profile} bijgewerkt, maar opnieuw verbinden is mislukt.", "error")
    else:
        flash(f"{profile} bijgewerkt.", "success")
    return redirect(url_for("web.wifi"))


@bp.route("/wifi/<profile>/remove", methods=["POST"])
def wifi_remove(profile):
    is_active = any(n["name"] == profile and n["active"] for n in wifi_manager.list_networks())

    # Extra confirmation step only for the network you're currently
    # browsing over - individual removal is otherwise explicit-but-direct,
    # per the "never auto-delete, but don't make removal a chore either"
    # requirement this feature was built around.
    if is_active and request.form.get("confirmed") != "yes":
        return render_template("wifi_confirm_remove.html", profile=profile)

    try:
        wifi_manager.remove_network(profile)
        flash(f"{profile} verwijderd.", "success")
    except RuntimeError as e:
        flash(f"Verwijderen mislukt: {e}", "error")
    return redirect(url_for("web.wifi"))


@bp.route("/shutdown", methods=["GET", "POST"])
def shutdown():
    if request.method == "GET" or request.form.get("confirmed") != "yes":
        return render_template("shutdown_confirm.html")

    # Deferred so the confirmation page's response actually reaches the
    # browser before poweroff fires - button_listener.blank_and_shutdown()
    # itself blanks the physical display then calls `poweroff` directly,
    # the same unauthenticated action button A already performs.
    import threading
    from button_listener import blank_and_shutdown
    threading.Timer(1.5, blank_and_shutdown).start()
    return render_template("shutdown_confirm.html", shutting_down=True)
