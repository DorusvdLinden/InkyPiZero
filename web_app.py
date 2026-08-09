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


def main():
    app = create_app()
    # Not debug/reloader mode - that forks a second watcher process, doubling
    # RAM for no benefit on this headless, non-hot-reloaded target (Pi Zero W
    # RAM is tight - see docs/networking.md).
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
