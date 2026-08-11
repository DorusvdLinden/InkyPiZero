"""Dev-time only: renders the app once per candidate `inky_saturation`
preset, each with icons regenerated to match, and saves both the "as
authored" render and the "as it'll actually look on the panel" simulation
(scripts/panel_sim.py) for every preset - so palette changes can be compared
side by side without a hardware round-trip. Not part of the running app.

Every widget draws from the single `widgets.palette.PALETTE` singleton, so
swapping `PALETTE.set_saturation(...)` before a render is enough to re-color
everything (chart, gauges, forecast cards) consistently - only the baked
icon PNGs need a separate regenerate() pass, since those are pre-rendered
files rather than drawn per-frame.

Usage: python scripts/color_options.py
"""

import os
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, REPO_DIR)
os.chdir(REPO_DIR)

from config import DisplayConfig
from weather_data import fetch_snapshot
from canvas import WeatherCanvas
from widgets.icons import AssetStore
from widgets.palette import PALETTE
from scripts import generate_icons
from scripts.panel_sim import simulate_panel

FONT_DIR = os.path.join(REPO_DIR, "assets", "fonts")
OUT_DIR = os.path.join(REPO_DIR, "mock_display_output", "color_palette_test")

PRESETS = [
    ("vivid_sat1.0", 1.0, "Full colors only - pure saturated ink, most vivid"),
    ("balanced_sat0.5", 0.5, "50% mix - current InkyDriver default"),
    ("soft_sat0.0", 0.0, "Desaturated - flat RGB primaries, paper-shifted"),
]

LOCATIONS = [
    ("sittard_netherlands", DisplayConfig(latitude=51.0004365, longitude=5.8993687, timezone="Europe/Amsterdam")),
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, saturation, notes in PRESETS:
        print(f"\n=== {name}: {notes} ===")
        PALETTE.set_saturation(saturation)

        icon_dir = os.path.join(OUT_DIR, f"icons_{name}")
        generate_icons.regenerate(icon_dir)
        assets = AssetStore(icon_dir, FONT_DIR)

        for loc_name, config in LOCATIONS:
            data = fetch_snapshot(config)
            image = WeatherCanvas(assets, config).render(data)
            authored_path = os.path.join(OUT_DIR, f"{name}_{loc_name}_authored.png")
            sim_path = os.path.join(OUT_DIR, f"{name}_{loc_name}_panel_sim.png")
            image.save(authored_path)
            simulate_panel(image, saturation=saturation).save(sim_path)
            print(f"  {loc_name}: {authored_path}")
            print(f"  {loc_name}: {sim_path}")

    PALETTE.set_saturation(0.5)  # restore the default for anything imported after this runs


if __name__ == "__main__":
    main()
