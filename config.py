from dataclasses import dataclass


@dataclass
class DisplayConfig:
    """Everything needed to fetch and render one weather snapshot.

    Defaults mirror the current InkyPi weather plugin instance in
    src/config/device.json (Sittard, NL / OpenMeteo / metric).
    """
    latitude: float = 51.0004365
    longitude: float = 5.8993687
    timezone: str = "Europe/Amsterdam"
    time_format: str = "24h"       # "24h" | "12h"
    forecast_days: int = 7
    graph_icon_step: int = 2
    show_moon_phase: bool = False
    background_color: str = "#ffffff"
    text_color: str = "#000000"
    inky_saturation: float = 0.0
    # 0 = no extra throttling beyond the fixed 10-minute systemd timer tick
    # (install/pi-weather-display.timer) - raising this skips a check
    # entirely (before even fetching weather data) until this many minutes
    # have passed since the last one. See display_freshness.py.
    min_update_interval_minutes: int = 0
    # How long the physical display can go unrefreshed even when the main
    # icon/temperature haven't changed, so slower-moving details (forecast
    # cards, the hourly chart, "Laatste update") don't go stale forever.
    # See display_freshness.py.
    force_refresh_max_stale_minutes: int = 60
