# Networking

How WiFi provisioning and the always-on settings web UI manage the device's
network connection. See [settings.md](./settings.md) for the settings the
web UI exposes, and [troubleshooting.md](./troubleshooting.md) if something's
not connecting.

## NetworkManager, not wpa_supplicant/dhcpcd directly

The deployed hardware (Raspberry Pi OS 13 "trixie") uses **NetworkManager**
as its network manager (`wpa_supplicant` runs underneath it as a backend;
`dhcpcd` is inactive). All WiFi profile management in this project goes
through `nmcli` - no custom credential storage, no hand-rolled
`wpa_supplicant.conf` editing. Saved networks live in NetworkManager's own
store at `/etc/NetworkManager/system-connections/*.nmconnection` (root-only,
mode 600).

## netplan is present but inert for this purpose - verified, not assumed

Raspberry Pi OS also has netplan installed, which could plausibly have been
a real risk: if netplan were the authoritative source of truth and
re-asserted its own config on every boot, it could silently wipe out
additional WiFi profiles this feature creates via `nmcli`.

This was checked empirically against the real deployed Pi, not assumed from
reading config alone:

1. Both existing files under `/etc/netplan/` are auto-generated
   `90-NM-<uuid>.yaml` passthrough exports (one per NetworkManager
   connection that existed at imaging time), each with `renderer:
   NetworkManager` - meaning NetworkManager is authoritative and these files
   are just its own state mirrored out to netplan's format, not the reverse.
2. **Empirical proof**: created a throwaway NetworkManager profile directly
   via `nmcli connection add`, rebooted the device, and confirmed after
   reboot that the profile survived completely untouched - and that netplan
   never even generated a `90-NM-*.yaml` file for it. netplan only tracks
   the specific profiles it created at image-build/first-boot time; it does
   not scan, mirror, or manage anything created afterward.

**Conclusion**: `nmcli`-created station-network profiles added via the web
UI are safe from netplan interference. No self-healing/idempotent-recreation
workaround is needed in `wifi_manager.py` on this account.

## AP hosting: hostapd, not NetworkManager's native hotspot

NetworkManager can host its own WiFi AP directly (a connection profile with
`802-11-wireless.mode ap`), and that was the first approach tried here. It
does not work reliably on this hardware - confirmed via three separate live
tests against the deployed Pi Zero W, all failing the same way:

```
NetworkManager[601]: Activation: (wifi) Hotspot network creation took too long, failing activation
NetworkManager[601]: device (wlan0): state change: config -> failed (reason 'supplicant-timeout')
```

This is NetworkManager's own hotspot implementation failing internally, not
a timeout-tuning problem - a 45s timeout plus one retry both hit the same
error. The kernel/driver itself correctly advertises AP capability
(`iw list` lists `AP` under "Supported interface modes" for this chip), so
the hardware isn't the limitation: NetworkManager's hotspot mode drives
WPA-PSK AP mode through `wpa_supplicant`'s own (fairly limited) AP support
rather than a purpose-built AP daemon, and that combination is a known weak
spot on some Broadcom chips including this one (Pi Zero W).

**Fix: hostapd**, the standard, purpose-built AP daemon for exactly this on
Raspberry Pi hardware. `wifi_manager.py`'s `ensure_ap_mode()` now:

1. Writes `/etc/hostapd/pi-weather-ap.conf` and a dedicated
   `/etc/dnsmasq-pi-weather-ap.conf` (DHCP for the AP's own subnet only -
   entirely separate from any system-wide dnsmasq, which doesn't exist as a
   persistent service on this image anyway).
2. Hands `wlan0` from NetworkManager to hostapd
   (`nmcli device set wlan0 managed no`), assigns the static AP address
   directly (`ip addr add 192.168.4.1/24 dev wlan0`).
3. Starts two on-demand, never-boot-enabled systemd units,
   `pi-weather-hostapd.service` and `pi-weather-ap-dnsmasq.service` -
   started/stopped only by `wifi_manager.py` itself, never by systemd at
   boot.

`connect()` reverses this (stop hostapd/dnsmasq, hand `wlan0` back to
NetworkManager as `managed yes`) before bringing up a station network, since
a single WiFi radio can only be AP or station at once.

**Verified live end-to-end** on the deployed Pi: hostapd came up in ~14s
(vs. NetworkManager's native mode never successfully completing even at
45s+), the e-paper setup screen genuinely rendered
(`setup_screen.render_setup_screen()` → `InkyDriver.show()`, confirmed via
`journalctl`: "Displaying image to Inky display"), and reconnecting back to
the real station network worked cleanly - `pi-weather-display.timer` and
`pi-weather-buttons.service` were completely undisturbed throughout every
test, confirming the render pipeline really is independent of WiFi state as
designed.

The distro's own `hostapd.service` unit ships **masked** by default on this
image (confirmed via `systemctl status hostapd`), so there's no risk of it
fighting the custom-named `pi-weather-hostapd.service` for the radio -
`install.sh` also explicitly disables it as a defensive measure in case a
future OS image ships it unmasked.

## Security posture - explicit, not accidental

Nothing in this feature has authentication: settings edits, WiFi credential
add/edit/remove, and the shutdown button are all reachable by anyone who can
reach the device's IP (or join its setup AP). This matches the project's
existing precedent - the physical button A already performs unauthenticated
shutdown - and its stated single-user/trusted-LAN threat model. Explicitly
out of scope: TLS/HTTPS, a login page, CSRF protection, rate limiting. If
this device is ever exposed beyond a trusted home LAN, that assumption no
longer holds and would need revisiting.
