"""Entry point for the always-on settings/WiFi-management web UI - the
`pi-weather-web.service` ExecStart target. Runs as its own persistent
systemd service, completely independent of the render timer
(`pi-weather-display.timer`/`main.py`) - see docs/networking.md for why one
Flask process can serve both the WiFi setup flow and the normal settings UI
without needing to know which network mode is currently active."""

import logging
import os
import secrets

from flask import Flask

import settings_store
import wifi_manager
from web.routes import bp

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_app() -> Flask:
    # Flask resolves template_folder/static_folder relative to this file's
    # own location by default (repo root) - point them at web/ explicitly
    # rather than moving templates/static up a level.
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "web", "templates"),
        static_folder=os.path.join(BASE_DIR, "web", "static"),
    )
    app.secret_key = secrets.token_hex(16)  # flash messages only, no auth/sessions to protect
    app.register_blueprint(bp)
    return app


def _show_setup_screen(config, ssid, password):
    # Imports deferred so Pillow/inky only ever load into this process's
    # memory when actually needed, not on every normal (already-connected)
    # startup - RAM is tight on a Pi Zero W (see docs/networking.md).
    from widgets.icons import AssetStore
    from setup_screen import render_setup_screen
    from display.inky_driver import InkyDriver

    assets = AssetStore(os.path.join(BASE_DIR, "assets", "icons"), os.path.join(BASE_DIR, "assets", "fonts"))
    image = render_setup_screen(assets, config, ssid, password, wifi_manager.AP_SETUP_URL)
    InkyDriver(saturation=config.inky_saturation).show(image)


def _ensure_network_ready():
    """Runs once at service startup, before app.run(): if wlan0 isn't
    associated with a known station network, activates this device's own
    setup AP and shows its SSID/password on the e-paper display - the one
    channel guaranteed available regardless of network state. Best-effort -
    a failure here (e.g. nmcli/inky trouble) is logged, not fatal, since the
    settings UI should still come up and be reachable if it's already on a
    working network."""
    try:
        if wifi_manager.is_connected():
            return
        logger.info("No known WiFi network reachable - activating setup AP")
        ssid, password = wifi_manager.ensure_ap_mode()
        logger.info("Setup AP active: ssid=%r", ssid)
        _show_setup_screen(settings_store.load_config(), ssid, password)
    except Exception:
        logger.exception("Startup connectivity/AP check failed - continuing anyway")


def main():
    _ensure_network_ready()
    app = create_app()
    # Not debug/reloader mode - that forks a second watcher process, doubling
    # RAM for no benefit on this headless, non-hot-reloaded target (Pi Zero W
    # RAM is tight - see docs/networking.md).
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
