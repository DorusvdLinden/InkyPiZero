"""Wraps NetworkManager (`nmcli`) for WiFi provisioning: hosting this
device's own setup access point when no known network is reachable, and
managing multiple saved station-network credentials the rest of the time.
NetworkManager's own connection-profile store
(/etc/NetworkManager/system-connections/) is the only credential storage -
no custom database, no wpa_supplicant.conf editing. See docs/networking.md
for why it's safe to build directly on nmcli on this hardware (netplan,
also present, was empirically confirmed not to interfere).

Every nmcli invocation uses list-form subprocess args, never shell=True/
f-string command lines, since SSIDs and passwords can contain spaces,
quotes, and non-ASCII characters that would otherwise be a shell-quoting
hazard."""

import logging
import secrets
import subprocess
import time

logger = logging.getLogger(__name__)

WIFI_INTERFACE = "wlan0"
AP_PROFILE_NAME = "pi-weather-ap"
AP_SSID_PREFIX = "InkyPiZero-Setup-"
AP_IPV4_ADDRESS = "192.168.4.1/24"
AP_SETUP_URL = "http://192.168.4.1"

MIN_PSK_LENGTH = 8  # WPA2 minimum


def _nmcli(*args: str, timeout: int = 15) -> str:
    """Raises RuntimeError uniformly for every failure mode (nonzero exit,
    timeout, or `nmcli` not even being installed - e.g. on a local dev
    machine without NetworkManager) so every caller only needs to catch one
    exception type."""
    try:
        result = subprocess.run(["nmcli", *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(f"nmcli {' '.join(args)} could not run: {e}") from e
    if result.returncode != 0:
        raise RuntimeError(f"nmcli {' '.join(args)} failed: {result.stderr.strip()}")
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


def is_connected() -> bool:
    """True if wlan0 is fully associated to a station (non-AP) network."""
    state = _wlan0_state()
    state_code = state.get("GENERAL.STATE", "").split()[0] if state.get("GENERAL.STATE") else ""
    if state_code != "100":
        return False
    active_name = state.get("GENERAL.CONNECTION", "")
    return active_name not in ("", "--", AP_PROFILE_NAME)


def current_mode() -> str:
    """"ap" | "station" | "disconnected" """
    active_name = _wlan0_state().get("GENERAL.CONNECTION", "")
    if active_name == AP_PROFILE_NAME:
        return "ap"
    if active_name and active_name != "--":
        return "station"
    return "disconnected"


def _ensure_ap_profile_exists() -> tuple[str, str]:
    """Creates the AP connection profile on first use (idempotent - the
    password is generated once and never regenerated, or the password
    printed/displayed on the e-paper screen would drift from what's
    actually configured). Returns (ssid, password)."""
    existing = {c["name"] for c in _list_connections()}
    if AP_PROFILE_NAME not in existing:
        ssid = f"{AP_SSID_PREFIX}{_mac_suffix()}"
        password = secrets.token_urlsafe(9)  # ~12 url-safe chars
        _nmcli(
            "connection", "add", "type", "wifi", "ifname", WIFI_INTERFACE,
            "con-name", AP_PROFILE_NAME, "autoconnect", "no",
            "ssid", ssid,
            "802-11-wireless.mode", "ap", "802-11-wireless.band", "bg",
            "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password,
            "ipv4.method", "shared", "ipv4.addresses", AP_IPV4_ADDRESS,
            "ipv6.method", "disabled",
        )
        logger.info("Created AP profile %r (ssid=%r)", AP_PROFILE_NAME, ssid)
        return ssid, password
    ssid = _nmcli("-g", "802-11-wireless.ssid", "connection", "show", AP_PROFILE_NAME)
    password = _nmcli("-s", "-g", "802-11-wireless-security.psk", "connection", "show", AP_PROFILE_NAME)
    return ssid, password


def ap_credentials() -> tuple[str, str]:
    """(ssid, password) for the setup AP - creates the profile if this is
    the first time it's needed, without activating it."""
    return _ensure_ap_profile_exists()


def ensure_ap_mode() -> tuple[str, str]:
    """Creates the AP profile if needed and activates it. Returns (ssid,
    password) for display on the e-paper setup screen.

    Uses a longer timeout than most nmcli calls and one retry: bringing up
    shared/AP mode means NetworkManager also has to stand up its own
    internal DHCP/NAT for the interface, not just associate, and on a real
    Pi Zero W the WiFi chip switching mode (especially right after having
    just been in station mode) can be slow enough to time out once or fail
    with a transient "supplicant took too long to authenticate" error on
    the first attempt - confirmed empirically. A short pause before retrying
    gives the hardware a moment to settle."""
    ssid, password = _ensure_ap_profile_exists()
    try:
        _nmcli("connection", "up", AP_PROFILE_NAME, timeout=45)
    except RuntimeError as e:
        logger.warning("First AP activation attempt failed (%s), retrying once", e)
        time.sleep(5)
        _nmcli("connection", "up", AP_PROFILE_NAME, timeout=45)
    return ssid, password


def list_networks() -> list[dict]:
    """Saved station networks (excludes the AP profile and non-WiFi
    profiles like ethernet/loopback), each as {"name": str, "active": bool}.
    Returns an empty list rather than raising if nmcli itself is
    unavailable (e.g. local dev without NetworkManager)."""
    active_name = _wlan0_state().get("GENERAL.CONNECTION", "")
    try:
        connections = _list_connections()
    except RuntimeError:
        return []
    return [
        {"name": c["name"], "active": c["name"] == active_name}
        for c in connections
        if c["type"] == "802-11-wireless" and c["name"] != AP_PROFILE_NAME
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


def edit_network(profile: str, password: str) -> None:
    """Updates an existing saved network's password (SSID rename isn't
    supported - remove + re-add for that)."""
    _validate_password(password)
    _nmcli("connection", "modify", profile, "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password)


def remove_network(profile: str) -> None:
    """Deletes a saved network profile - explicit/individual only, never
    automatic (a whole-list "forget everything" action doesn't exist here
    by design)."""
    _nmcli("connection", "delete", profile)


def connect(profile: str) -> bool:
    """Activates a saved profile (station network or the AP) - NetworkManager
    handles deactivating whatever else is currently active on the radio.
    Returns True on success, False if the connection attempt failed (e.g.
    wrong password, network out of range) rather than raising, since a
    failed connect is an expected, recoverable outcome for callers."""
    try:
        _nmcli("connection", "up", profile, timeout=30)
        return True
    except RuntimeError as e:
        logger.warning("Failed to connect to %r: %s", profile, e)
        return False
