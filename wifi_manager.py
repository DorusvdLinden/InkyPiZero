"""WiFi provisioning: hosting this device's own setup access point when no
known network is reachable, and managing multiple saved station-network
credentials the rest of the time.

Station networks are managed entirely through NetworkManager (`nmcli`) -
its own connection-profile store (/etc/NetworkManager/system-connections/)
is the only credential storage for them, no custom database, no
wpa_supplicant.conf editing. See docs/networking.md for why it's safe to
build directly on nmcli on this hardware (netplan, also present, was
empirically confirmed not to interfere).

The setup AP itself is hosted by **hostapd** + a dedicated dnsmasq instance
instead, with wlan0 temporarily handed off from NetworkManager
(`nmcli device set wlan0 managed no`) while they run - NetworkManager's own
native hotspot mode (which drives WPA-PSK AP mode through wpa_supplicant
rather than a purpose-built AP daemon) was tried first and reproducibly
failed on a real Pi Zero W ("Hotspot network creation took too long" /
supplicant-timeout, every single time), confirmed via the kernel/driver
itself correctly advertising AP-mode support (`iw list`) - the failure was
specifically in NetworkManager's own AP implementation, not the hardware.
hostapd is the standard, purpose-built tool for exactly this on Raspberry
Pi hardware. The AP's own credentials are persisted separately (a small
JSON file) since they're no longer an NetworkManager connection profile.

Every subprocess invocation uses list-form args, never shell=True/f-string
command lines, since SSIDs and passwords can contain spaces, quotes, and
non-ASCII characters that would otherwise be a shell-quoting hazard."""

import json
import logging
import os
import secrets
import subprocess
import time

logger = logging.getLogger(__name__)

WIFI_INTERFACE = "wlan0"
AP_SSID_PREFIX = "InkyPiZero-"
AP_IPV4_ADDRESS = "192.168.4.1/24"
AP_IP = AP_IPV4_ADDRESS.split("/")[0]
AP_SETUP_URL = f"http://{AP_IP}"
AP_DHCP_RANGE = ("192.168.4.10", "192.168.4.100")

# Lowercase letters + digits only, excluding characters that are easy to
# misread/mistype on a phone keyboard (0/o, 1/l/i) - still randomly
# generated and unique per device, just quick to type accurately while
# looking back and forth between the e-paper screen and a phone.
AP_PASSWORD_CHARS = "abcdefghjkmnpqrstuvwxyz23456789"
AP_PASSWORD_LENGTH = 10

HOSTAPD_CONF_PATH = "/etc/hostapd/pi-weather-ap.conf"
HOSTAPD_SERVICE = "pi-weather-hostapd.service"
DNSMASQ_AP_CONF_PATH = "/etc/dnsmasq-pi-weather-ap.conf"
DNSMASQ_AP_SERVICE = "pi-weather-ap-dnsmasq.service"
AP_CREDENTIALS_PATH = "/var/lib/pi-weather-display/ap_credentials.json"

MIN_PSK_LENGTH = 8  # WPA2 minimum


def _run(cmd: list[str], timeout: int = 15, check: bool = True) -> subprocess.CompletedProcess:
    """Generic subprocess runner for ip/systemctl calls (nmcli has its own
    wrapper below) - same list-form-args rationale as _nmcli()."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(f"{' '.join(cmd)} could not run: {e}") from e
    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {result.stderr.strip()}")
    return result


def _nmcli(*args: str, timeout: int = 15) -> str:
    """Raises RuntimeError uniformly for every failure mode (nonzero exit,
    timeout, or `nmcli` not even being installed - e.g. on a local dev
    machine without NetworkManager) so every caller only needs to catch one
    exception type."""
    result = _run(["nmcli", *args], timeout=timeout)
    return result.stdout.strip()


def _unescape(value: str) -> str:
    """nmcli's terse (-t) output escapes ':' and '\\' in field values with
    a leading backslash - undo that so callers see the real string."""
    return value.replace("\\:", ":").replace("\\\\", "\\")


def _nmcli_fields(target_args: list[str], fields: list[str]) -> dict[str, str]:
    """Runs `nmcli -t -f f1,f2,... <target_args>` and returns {field: value},
    one nmcli call for multiple fields at once."""
    raw = _nmcli("-t", "-f", ",".join(fields), *target_args)
    result = {}
    for line in raw.splitlines():
        field, _, value = line.partition(":")
        if field in fields:
            result[field] = _unescape(value)
    return result


def _mac_suffix() -> str:
    try:
        with open(f"/sys/class/net/{WIFI_INTERFACE}/address") as f:
            mac = f.read().strip()
        return mac.replace(":", "")[-4:].upper()
    except OSError:
        return "0000"


def _list_connections() -> list[dict]:
    """Every NetworkManager connection profile as {"name", "uuid", "type"}."""
    raw = _nmcli("-t", "-f", "NAME,UUID,TYPE", "connection", "show")
    connections = []
    for line in raw.splitlines():
        if not line:
            continue
        name, uuid, conn_type = line.split(":", 2)
        connections.append({"name": _unescape(name), "uuid": uuid, "type": conn_type})
    return connections


def _wlan0_state() -> dict[str, str]:
    try:
        return _nmcli_fields(["device", "show", WIFI_INTERFACE], ["GENERAL.STATE", "GENERAL.CONNECTION"])
    except RuntimeError:
        return {}


def _hostapd_active() -> bool:
    try:
        result = _run(["systemctl", "is-active", HOSTAPD_SERVICE], timeout=5, check=False)
        return result.stdout.strip() == "active"
    except RuntimeError:
        return False


def is_connected() -> bool:
    """True if wlan0 is fully associated to a station (non-AP) network."""
    if _hostapd_active():
        return False
    state = _wlan0_state()
    state_code = state.get("GENERAL.STATE", "").split()[0] if state.get("GENERAL.STATE") else ""
    if state_code != "100":
        return False
    active_name = state.get("GENERAL.CONNECTION", "")
    return active_name not in ("", "--")


def current_mode() -> str:
    """"ap" | "station" | "disconnected" """
    if _hostapd_active():
        return "ap"
    active_name = _wlan0_state().get("GENERAL.CONNECTION", "")
    if active_name and active_name != "--":
        return "station"
    return "disconnected"


def _get_or_create_ap_credentials() -> tuple[str, str]:
    """SSID is derived deterministically from the WiFi MAC (stable, no
    storage needed); the password is generated once and persisted - the
    e-paper screen (and anyone re-reading it later) must never see a
    password that doesn't match what's actually in hostapd.conf."""
    ssid = f"{AP_SSID_PREFIX}{_mac_suffix()}"
    try:
        with open(AP_CREDENTIALS_PATH) as f:
            password = json.load(f)["password"]
    except (OSError, json.JSONDecodeError, KeyError):
        password = "".join(secrets.choice(AP_PASSWORD_CHARS) for _ in range(AP_PASSWORD_LENGTH))
        os.makedirs(os.path.dirname(AP_CREDENTIALS_PATH), exist_ok=True)
        with open(AP_CREDENTIALS_PATH, "w") as f:
            json.dump({"password": password}, f)
        logger.info("Generated new setup-AP password")
    return ssid, password


def ap_credentials() -> tuple[str, str]:
    """(ssid, password) for the setup AP - creates/persists them if this is
    the first time they're needed, without activating anything."""
    return _get_or_create_ap_credentials()


def _write_hostapd_config(ssid: str, password: str):
    conf = (
        f"interface={WIFI_INTERFACE}\n"
        "driver=nl80211\n"
        f"ssid={ssid}\n"
        "hw_mode=g\n"
        "channel=6\n"
        "wpa=2\n"
        f"wpa_passphrase={password}\n"
        "wpa_key_mgmt=WPA-PSK\n"
        "wpa_pairwise=CCMP\n"
        "rsn_pairwise=CCMP\n"
        "auth_algs=1\n"
        "wmm_enabled=1\n"
    )
    with open(HOSTAPD_CONF_PATH, "w") as f:
        f.write(conf)


def _write_dnsmasq_ap_config():
    range_start, range_end = AP_DHCP_RANGE
    conf = (
        f"interface={WIFI_INTERFACE}\n"
        "bind-interfaces\n"
        "except-interface=lo\n"
        f"dhcp-range={range_start},{range_end},255.255.255.0,24h\n"
        f"dhcp-option=3,{AP_IP}\n"
        f"dhcp-option=6,{AP_IP}\n"
        # Wildcard DNS - resolves *every* domain to this device's own IP
        # while the setup AP is active, so opening any URL in a browser
        # (not just AP_SETUP_URL) lands on the setup page, matching
        # commercial IoT captive-portal behavior. Combined with the DHCP
        # option 6 above (this device as the DNS server), clients get
        # this automatically - no extra client-side config. Not a *real*
        # captive-portal redirect (no 802.11u/OS-level "sign in to
        # network" popup, no HTTP redirect for HTTPS requests, which will
        # just fail TLS validation against this device's IP) - just DNS,
        # which is enough for a manually-opened plain HTTP URL.
        f"address=/#/{AP_IP}\n"
    )
    with open(DNSMASQ_AP_CONF_PATH, "w") as f:
        f.write(conf)


def ensure_ap_mode() -> tuple[str, str]:
    """Hands wlan0 over to hostapd + a dedicated dnsmasq instance and
    activates the setup AP. Returns (ssid, password) for display on the
    e-paper setup screen."""
    ssid, password = _get_or_create_ap_credentials()
    _write_hostapd_config(ssid, password)
    _write_dnsmasq_ap_config()

    _run(["nmcli", "device", "set", WIFI_INTERFACE, "managed", "no"])
    _run(["ip", "addr", "flush", "dev", WIFI_INTERFACE])
    _run(["ip", "addr", "add", AP_IPV4_ADDRESS, "dev", WIFI_INTERFACE])
    _run(["ip", "link", "set", WIFI_INTERFACE, "up"])
    _run(["systemctl", "restart", HOSTAPD_SERVICE], timeout=20)
    _run(["systemctl", "restart", DNSMASQ_AP_SERVICE], timeout=20)
    logger.info("Setup AP active: ssid=%r", ssid)
    return ssid, password


def _teardown_ap_mode():
    """Stops hostapd/dnsmasq and hands wlan0 back to NetworkManager - best
    effort, since this runs as part of recovering into a working station
    connection and shouldn't itself block on a service that's already
    half-stopped."""
    _run(["systemctl", "stop", HOSTAPD_SERVICE], check=False)
    _run(["systemctl", "stop", DNSMASQ_AP_SERVICE], check=False)
    _run(["ip", "addr", "flush", "dev", WIFI_INTERFACE], check=False)
    _run(["nmcli", "device", "set", WIFI_INTERFACE, "managed", "yes"], check=False)
    time.sleep(2)  # give NetworkManager a moment to pick the device back up


def list_networks() -> list[dict]:
    """Saved station networks (excludes non-WiFi profiles like
    ethernet/loopback), each as {"name": str, "active": bool}. Returns an
    empty list rather than raising if nmcli itself is unavailable (e.g.
    local dev without NetworkManager)."""
    active_name = _wlan0_state().get("GENERAL.CONNECTION", "")
    try:
        connections = _list_connections()
    except RuntimeError:
        return []
    return [
        {"name": c["name"], "active": c["name"] == active_name}
        for c in connections
        if c["type"] == "802-11-wireless"
    ]


def _validate_password(password: str | None):
    if password and len(password) < MIN_PSK_LENGTH:
        raise ValueError(f"WiFi password must be at least {MIN_PSK_LENGTH} characters")


def add_network(ssid: str, password: str | None) -> None:
    """Saves a new station network profile. `password` empty/None adds an
    open network with no security."""
    _validate_password(password)
    args = [
        "connection", "add", "type", "wifi", "ifname", WIFI_INTERFACE,
        "con-name", ssid, "ssid", ssid,
        "connection.autoconnect", "yes", "connection.autoconnect-priority", "10",
    ]
    if password:
        args += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password]
    _nmcli(*args)


def edit_network(profile: str, password: str, new_ssid: str | None = None) -> None:
    """Updates an existing saved network's password and/or SSID, both
    independently optional - a blank password leaves the existing one
    untouched (doesn't overwrite it with an empty psk), and `new_ssid`
    renames in place: updates both the connection profile's display name
    and its actual broadcast SSID (add_network always keeps these equal,
    so this stays consistent with new profiles) via a single `connection
    modify` - no remove + re-add needed. For when the real-world router's
    SSID changed and the saved profile needs to match, not just a
    cosmetic rename."""
    if new_ssid is not None:
        new_ssid = new_ssid.strip()
    if not password and not new_ssid:
        return
    args = ["connection", "modify", profile]
    if password:
        _validate_password(password)
        args += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password]
    if new_ssid and new_ssid != profile:
        args += ["802-11-wireless.ssid", new_ssid, "connection.id", new_ssid]
    _nmcli(*args)


def remove_network(profile: str) -> None:
    """Deletes a saved network profile - explicit/individual only, never
    automatic (a whole-list "forget everything" action doesn't exist here
    by design)."""
    _nmcli("connection", "delete", profile)


def connect(profile: str) -> bool:
    """Activates a saved station profile - tears down the setup AP first if
    that's currently active (hostapd and a station connection can't share
    the one WiFi radio), then lets NetworkManager handle the rest. Returns
    True on success, False if the connection attempt failed (e.g. wrong
    password, network out of range) rather than raising, since a failed
    connect is an expected, recoverable outcome for callers."""
    if current_mode() == "ap":
        _teardown_ap_mode()
    try:
        _nmcli("connection", "up", profile, timeout=30)
        return True
    except RuntimeError as e:
        logger.warning("Failed to connect to %r: %s", profile, e)
        return False
