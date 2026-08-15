"""Deterministic coverage for the PALETTE/config.inky_saturation sync fix -
not part of the app. Confirms WeatherCanvas and render_setup_screen (the
app's two actual rendering entry points) both keep the shared
widgets.palette.PALETTE singleton in sync with whatever DisplayConfig they
were built from, instead of it staying frozen at its own hardcoded default
forever - see docs/plans/palette-saturation-sync-fix.md and TODO.md's
"Color palette & quantization" section. No network/hardware needed.
"""

import os
import sys

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)
os.chdir(REPO_DIR)

from config import DisplayConfig
from canvas import WeatherCanvas
from setup_screen import render_setup_screen
from weather_data import get_uv_color
from widgets.icons import AssetStore
from widgets.palette import PALETTE, native_colors

ICON_DIR = os.path.join(REPO_DIR, "assets", "icons")
FONT_DIR = os.path.join(REPO_DIR, "assets", "fonts")

DEFAULT_SATURATION = 0.0  # DisplayConfig's own default (config.py) - restored after every test


def test_weather_canvas_syncs_palette():
    assets = AssetStore(ICON_DIR, FONT_DIR)
    config = DisplayConfig(inky_saturation=0.7)
    WeatherCanvas(assets, config)
    return PALETTE.saturation == 0.7


def test_weather_canvas_resyncs_on_later_construction():
    """A second WeatherCanvas built from a different config must move the
    shared singleton again, not leave it stuck at the first one's value -
    this is the actual bug scenario (main.py loads whatever config is
    currently saved fresh on every one-shot run)."""
    assets = AssetStore(ICON_DIR, FONT_DIR)
    WeatherCanvas(assets, DisplayConfig(inky_saturation=0.7))
    WeatherCanvas(assets, DisplayConfig(inky_saturation=0.2))
    return PALETTE.saturation == 0.2


def test_render_setup_screen_syncs_palette():
    assets = AssetStore(ICON_DIR, FONT_DIR)
    config = DisplayConfig(inky_saturation=0.3)
    render_setup_screen(assets, config, "TestSSID", "hunter2", "http://192.168.4.1")
    return PALETTE.saturation == 0.3


def test_get_uv_color_uses_the_saturation_it_is_given():
    """weather_data.get_uv_color() takes saturation as an explicit
    argument rather than reading the shared PALETTE.saturation - unlike
    the tests above, fetch_snapshot() (which calls this) always runs
    *before* WeatherCanvas.__init__ syncs PALETTE for that render, so
    reading the singleton here would silently use whatever saturation it
    was last synced to instead of this render's actual configured value.
    Found 2026-08-15 while fixing the identical bug pattern for the
    forecast-card weather-quality border color - this test exists because
    the other three tests in this file, which only check PALETTE.saturation
    after a WeatherCanvas/render_setup_screen call, would never have caught
    it (get_uv_color runs earlier, in fetch_snapshot)."""
    color_a = get_uv_color(7, 0.0)
    color_b = get_uv_color(7, 0.7)
    expected_a = "#{:02x}{:02x}{:02x}".format(*native_colors(0.0)["orange"])
    expected_b = "#{:02x}{:02x}{:02x}".format(*native_colors(0.7)["orange"])
    return color_a == expected_a and color_b == expected_b and color_a != color_b


TESTS = [
    test_weather_canvas_syncs_palette,
    test_weather_canvas_resyncs_on_later_construction,
    test_render_setup_screen_syncs_palette,
    test_get_uv_color_uses_the_saturation_it_is_given,
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
        finally:
            PALETTE.set_saturation(DEFAULT_SATURATION)
        results.append((test.__name__, ok))

    print("\n--- Summary ---")
    for name, ok in results:
        print(f"{'OK' if ok else 'FAIL':8s} {name}")

    if not all(ok for _, ok in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
