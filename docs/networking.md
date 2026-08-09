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

**Conclusion**: `nmcli`-created profiles (both the AP profile and any
station networks added via the web UI) are safe from netplan interference.
No self-healing/idempotent-recreation workaround is needed in
`wifi_manager.py` on this account.

## Security posture - explicit, not accidental

Nothing in this feature has authentication: settings edits, WiFi credential
add/edit/remove, and the shutdown button are all reachable by anyone who can
reach the device's IP (or join its setup AP). This matches the project's
existing precedent - the physical button A already performs unauthenticated
shutdown - and its stated single-user/trusted-LAN threat model. Explicitly
out of scope: TLS/HTTPS, a login page, CSRF protection, rate limiting. If
this device is ever exposed beyond a trusted home LAN, that assumption no
longer holds and would need revisiting.
