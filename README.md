# InkyPiZero

<img src="./docs/images/inky_clock.jpg" />

## About

A weather-only E-Ink display, built for a Raspberry Pi driving a Pimoroni Inky
Impression panel. It renders natively with Pillow (no browser, no Chromium)
and runs as a lightweight, periodic job instead of a long-running web app -
just fetch the forecast, draw it, push it to the display, repeat.

This project started as a fork of [fatihak/InkyPi](https://github.com/fatihak/InkyPi),
a full multi-plugin E-Ink dashboard with a web UI, then split off into its own
repo once it no longer shared any code with that app - just the weather
plugin's logic, ported and stripped down to a single purpose: a minimal,
low-overhead weather display suitable for weaker hardware (e.g. a Raspberry
Pi Zero W) that can't comfortably run a headless browser.

**Features**:
- Current conditions, an hourly temperature/rain chart, and a multi-day
  forecast, all hand-drawn with Pillow
- No web UI, no plugins, no playlist scheduling - configuration is a single
  Python file
- Runs as a `systemd` timer (e.g. every 10 minutes), not a persistent service
- Weather data from [Open-Meteo](https://open-meteo.com/) - no API key needed
- Press button A on the back of the Inky Impression to blank the screen and
  safely shut the Pi down

## Hardware

- Raspberry Pi (Zero W, Zero 2 W, 3, or 4)
- MicroSD Card (min 8 GB) like [this one](https://amzn.to/3G3Tq9W)
- E-Ink Display: Inky Impression by Pimoroni
    - **[13.3 Inch Display](https://collabs.shop/q2jmza)**
    - **[7.3 Inch Display](https://collabs.shop/q2jmza)**
    - **[5.7 Inch Display](https://collabs.shop/ns6m6m)**
    - **[4 Inch Display](https://collabs.shop/cpwtbh)**
- Picture Frame or 3D Stand - see [community.md](./docs/community.md) for
  community-submitted 3D models, custom builds, and other frame ideas

**Disclosure:** The links above are affiliate links (carried over from the
upstream project this was forked from).

## Installation

1. Flash Raspberry Pi OS onto your SD card - see
   [installation.md](./docs/installation.md) for detailed steps.
2. Clone the repository and run the installer:
    ```bash
    git clone git@github.com:DorusvdLinden/InkyPiZero.git
    cd InkyPiZero
    sudo bash install/install.sh
    ```
3. **Edit `config.py`** to set your location (`latitude`/`longitude`) and
   preferences - there's no web UI, so this is done directly in the source
   file.
4. Reboot if the installer enabled SPI for the first time.

The installer sets up its own minimal Python virtual environment and a
`pi-weather-display.timer` systemd unit that renders and updates the display
every 10 minutes.

Useful commands after installing:

```bash
systemctl status pi-weather-display.timer     # confirm the timer is active
journalctl -u pi-weather-display.service      # view render logs
sudo systemctl start pi-weather-display.service  # force an immediate render
systemctl status pi-weather-shutdown.service  # confirm the button listener is active
```

To update: `git pull` then rerun `sudo bash install/install.sh` (safe to
rerun - reinstalls the venv dependencies and refreshes the systemd units in
place).

To uninstall: `sudo bash install/uninstall.sh` (removes the systemd
service/timer and its virtual environment; your git checkout and
`config.py` are left untouched).

See [development.md](./docs/development.md) for local (no-hardware) testing.

## Architecture

- `weather_data.py` - fetches and parses Open-Meteo data (current, hourly,
  daily forecast, air quality/UV) into typed dataclasses
- `layout.py` - fixed pixel regions for the 800x480 canvas
- `canvas.py` - orchestrates one full render (`WeatherCanvas.render()`)
- `widgets/` - gauge (wind/pressure/UV/AQI), chart (temp/rain), forecast-card,
  and icon/humidity-drop drawing - all hand-drawn with Pillow
- `display/inky_driver.py` - thin wrapper around the `inky` library;
  `display/mock_driver.py` saves to a file instead, for testing without
  hardware
- `assets/` - the icon PNGs and Jost font files it actually uses (see
  [attribution.md](./docs/attribution.md))
- `config.py` - a plain dataclass (location, units, refresh interval, etc.) -
  edited directly in source, since there's no web UI
- `main.py` - fetch -> render -> display, no scheduling loop of its own
  (that's the systemd timer's job)
- `shutdown_button.py` - listens for button A (GPIO5) and blanks the screen +
  powers off; unlike `main.py` this runs as its own persistent
  `pi-weather-shutdown.service`, since a button press can happen anytime
- `TODO.md` - known bugs and rough edges

Chosen over an ESP32-S3/embedded-C rewrite because it reuses Pimoroni's
existing `inky` Python display driver unchanged, and reuses the weather
data-fetch/parsing logic almost verbatim, rather than reimplementing the
whole visual layout in C.

## License

Distributed under the GPL 3.0 License, see [LICENSE](./LICENSE) for more
information.

This project includes fonts and icons with separate licensing and
attribution requirements. See [Attribution](./docs/attribution.md) for
details.

## Issues

Check out the [troubleshooting guide](./docs/troubleshooting.md).

If you're using a Pi Zero W, note that there are known issues during
installation - see
[Known Issues during Pi Zero W Installation](./docs/troubleshooting.md#known-issues-during-pi-zero-w-installation)
in the troubleshooting guide.

## Acknowledgements

This project is a fork of [InkyPi](https://github.com/fatihak/InkyPi) by
[fatihak](https://github.com/fatihak) - all credit for the original
multi-plugin app, web UI, and display driver integration goes there. Also
worth checking out:

- [PaperPi](https://github.com/txoof/PaperPi) - supports Waveshare devices
- [InkyCal](https://github.com/aceinnolab/Inkycal) - modular plugins for custom dashboards
- [PiInk](https://github.com/tlstommy/PiInk) - inspiration behind InkyPi's original Flask web UI
- [rpi_weather_display](https://github.com/sjnims/rpi_weather_display) - alternative eink weather dashboard with advanced power efficiency
