# InkyPiZero Detailed Installation

## Flashing Raspberry Pi OS 

1. Install the Raspberry Pi Imager from the [official download page](https://www.raspberrypi.com/software/)
2. Insert the target SD Card into your computer and launch the Raspberry Pi Imager software
    - Raspberry Pi Device: Choose your Pi model
    - Operating System: Select the recommended system
    - Storage: Select the target SD Card

<img src="./images/raspberry_pi_imager.png" alt="Raspberry Pi Imager" width="500"/>

3. Click Next and choose Edit Settings on the Use OS customization? screen
    - General:
        - Set hostname: enter your desired hostname
            -  This will be used to ssh into the device on your network
               (there's no web UI to access - see the main
               [README](../README.md)).
        - Set username & password
            - Do not use the default username and password on a Raspberry PI as this poses a security risk
        - Configure wireless LAN to your network
            - This is also the network you'll SSH in over - there's no web
              server to reach (see the main [README](../README.md))
        - Set local settings to your Time zone
    - Service:
        - Enable SSH:
            - Use password authentication
    - Options: leave default values

<p float="left">
  <img src="./images/raspberry_pi_imager_general.png" width="250" />
  <img src="./images/raspberry_pi_imager_options.png" width="250" /> 
  <img src="./images/raspberry_pi_imager_services.png" width="250" />
</p>

4. Click Yes to apply OS customization options and confirm

## Installing InkyPiZero

5. SSH into the Pi using the hostname/credentials set above:
    ```bash
    ssh <username>@<hostname>.local
    ```
6. Clone the repository and run the installer:
    ```bash
    git clone https://github.com/DorusvdLinden/InkyPiZero.git
    cd InkyPiZero
    sudo bash install/install.sh
    ```
    This creates its own Python virtual environment
    (`/usr/local/pi-weather-display/venv`), enables the SPI/I2C interfaces
    the Inky display needs, and installs two systemd units: a
    `pi-weather-display.timer` that renders and pushes to the display every
    10 minutes, and a persistent `pi-weather-buttons.service` that listens
    for the four physical buttons on the back of the panel.
7. Reboot if the installer enabled SPI/I2C for the first time (only needed
   on a fresh install, not on reinstalls/updates).

## Configuring your location and settings

There's no web UI - **edit `config.py`** directly (before or after
installing) to set your location (`latitude`/`longitude`) and every other
preference. See [settings.md](./settings.md) for the full reference of every
option, both the ones edited in `config.py`/passed as CLI flags and the ones
controlled live via the four physical buttons on the back of the display.

Changes to `config.py` take effect on the next render - no service restart
needed, or force one immediately:
```bash
sudo systemctl start pi-weather-display.service
```

## Verifying the install

```bash
systemctl status pi-weather-display.timer     # confirm the render timer is active
journalctl -u pi-weather-display.service      # view render logs
systemctl status pi-weather-buttons.service   # confirm the button listener is active
```

If something looks wrong, see [troubleshooting.md](./troubleshooting.md).
