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
    forecast_days: int = 7  # 1-14, see settings_store.MAX_FORECAST_DAYS
    graph_icon_step: int = 2
    background_color: str = "#ffffff"
    text_color: str = "#000000"
    inky_saturation: float = 0.0
    # "jost" | "bitter" - see widgets/icons.py's FONT_FAMILIES. Bitter is the
    # default (2026-08-11) - chosen over Jost after a real-hardware
    # comparison, see docs/changes.md. Also a web UI setting.
    font_family: str = "bitter"
    # "mm" | "category" - chart's rain axis: a plain mm number vs Dutch
    # intensity words (droog/motrgn/licht/matig/zwaar/hevig,
    # widgets/chart.py). "category" only applies to rain/hail windows -
    # snow/dry always show a plain number regardless.
    rain_axis_format: str = "mm"
    # "ms" | "beaufort" - the "Wind" data point's number: whole m/s, or the
    # Beaufort number (0-12, "bft"). Display only: data is always fetched
    # in m/s, and wind is never charted, so no axis logic is involved
    # (unlike the reverted imperial toggle, docs/changes.md entry 25).
    wind_speed_unit: str = "ms"
    # 0 = no extra throttling beyond the fixed 10-minute systemd timer tick
    # (install/pi-weather-display.timer) - raising this skips a check
    # entirely (before even fetching weather data) until this many minutes
    # have passed since the last one. See display_freshness.py.
    min_update_interval_minutes: int = 0
    # How long the physical display can go unrefreshed even when the main
    # icon/temperature haven't changed, so slower-moving details (forecast
    # cards, the hourly chart, "Laatste update") don't go stale forever.
    # See display_freshness.py.
    force_refresh_max_stale_minutes: int = 120
    # Minimum change (degrees) in the current temperature, versus the one on
    # screen, that refreshes the panel right away; smaller drift waits for
    # force_refresh_max_stale_minutes. See display_freshness.py.
    refresh_temp_delta: int = 2
    # Pluggable local weather-station source for "actual" (not modeled)
    # current temperature/rain - see weather_data.STATION_ADAPTERS. No real
    # station is wired up yet (only "generic_http", a placeholder) - these
    # fields exist so a real integration (Netatmo, Ecowitt, etc.) can be
    # added later purely inside weather_data.py. See docs/settings.md.
    station_enabled: bool = False
    station_type: str = ""       # "" (disabled) | a key in weather_data.STATION_ADAPTERS
    station_base_url: str = ""
    station_api_key: str = ""
