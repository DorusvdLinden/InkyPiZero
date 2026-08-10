"""Deterministic coverage for display_freshness.py's skip/force logic -
not part of the app. Runs entirely against a temp directory (monkeypatches
the module's STATE_PATH/FORCE_REFRESH_PATH) so it never touches the real
/var/lib/pi-weather-display/ state, and needs no network/hardware. Run
after any change to display_freshness.py, main.py's real-hardware render
path, or the forced-refresh sentinel call sites in button_listener.py/
web/routes.py - see CLAUDE.md.
"""

import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)
os.chdir(REPO_DIR)

import display_freshness

TMP_DIR = tempfile.mkdtemp(prefix="inkypizero_freshness_test_")
display_freshness.STATE_PATH = os.path.join(TMP_DIR, "display_freshness.json")
display_freshness.FORCE_REFRESH_PATH = os.path.join(TMP_DIR, "force_refresh_requested")

NOW = datetime(2026, 8, 10, 12, 0, 0)


def _reset():
    for path in (display_freshness.STATE_PATH, display_freshness.FORCE_REFRESH_PATH):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def test_first_run_always_updates():
    _reset()
    return display_freshness.should_update_display("01d", 20, NOW) is True


def test_unchanged_within_hour_skips():
    _reset()
    display_freshness.record_display("01d", 20, NOW)
    later = NOW + timedelta(minutes=30)
    return display_freshness.should_update_display("01d", 20, later) is False


def test_unchanged_past_hour_forces():
    _reset()
    display_freshness.record_display("01d", 20, NOW)
    later = NOW + timedelta(hours=1, minutes=1)
    return display_freshness.should_update_display("01d", 20, later) is True


def test_unchanged_exactly_one_hour_forces():
    _reset()
    display_freshness.record_display("01d", 20, NOW)
    later = NOW + timedelta(hours=1)
    return display_freshness.should_update_display("01d", 20, later) is True


def test_changed_icon_forces():
    _reset()
    display_freshness.record_display("01d", 20, NOW)
    later = NOW + timedelta(minutes=1)
    return display_freshness.should_update_display("53d", 20, later) is True


def test_changed_temp_forces():
    _reset()
    display_freshness.record_display("01d", 20, NOW)
    later = NOW + timedelta(minutes=1)
    return display_freshness.should_update_display("01d", 21, later) is True


def test_skipped_tick_does_not_reset_last_display_time():
    """A skip must not touch the stored state - only record_display() (an
    actual push) should, or the hourly force would never fire during a
    long unchanged-weather stretch of repeated skipped ticks."""
    _reset()
    display_freshness.record_display("01d", 20, NOW)
    just_shy = NOW + timedelta(minutes=59)
    if display_freshness.should_update_display("01d", 20, just_shy) is not False:
        return False
    past_hour_from_original = NOW + timedelta(hours=1, minutes=1)
    return display_freshness.should_update_display("01d", 20, past_hour_from_original) is True


def test_corrupt_state_file_forces():
    _reset()
    os.makedirs(TMP_DIR, exist_ok=True)
    with open(display_freshness.STATE_PATH, "w") as f:
        f.write("not valid json{{{")
    return display_freshness.should_update_display("01d", 20, NOW) is True


def test_forced_refresh_sentinel_consumed_once():
    _reset()
    before = display_freshness.consume_forced_refresh()
    display_freshness.request_forced_refresh()
    during = display_freshness.consume_forced_refresh()
    after = display_freshness.consume_forced_refresh()
    return (before, during, after) == (False, True, False)


TESTS = [
    test_first_run_always_updates,
    test_unchanged_within_hour_skips,
    test_unchanged_past_hour_forces,
    test_unchanged_exactly_one_hour_forces,
    test_changed_icon_forces,
    test_changed_temp_forces,
    test_skipped_tick_does_not_reset_last_display_time,
    test_corrupt_state_file_forces,
    test_forced_refresh_sentinel_consumed_once,
]


def main():
    results = []
    for test in TESTS:
        try:
            ok = test()
        except Exception as e:
            ok = False
            print(f"FAIL  {test.__name__:45s} raised {e!r}")
        else:
            print(f"{'OK' if ok else 'FAIL':6s}{test.__name__}")
        results.append((test.__name__, ok))

    shutil.rmtree(TMP_DIR, ignore_errors=True)

    print("\n--- Summary ---")
    for name, ok in results:
        print(f"{'OK' if ok else 'FAIL':8s} {name}")

    if not all(ok for _, ok in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
