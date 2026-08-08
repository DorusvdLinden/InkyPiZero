"""Dev-time only: simulates what an image will actually look like on the real
Inky Impression 7.3" (AC073TC1A, 7-color ACeP) panel, without needing a
hardware round-trip. Not part of the running app.

Thin wrapper around display/quantize.py's `quantize_for_panel()` - the same
function `InkyDriver.show()` uses for actual hardware output - so any
render can be previewed exactly as it will appear on the physical panel.
`dither`/`harden` are exposed here for A/B comparison against the pre-
hardening/Floyd-Steinberg behavior; real hardware output always uses the
defaults (nearest-color + hardened neutral edges).
"""

import os
import sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from display.quantize import quantize_for_panel


def simulate_panel(image: Image.Image, saturation: float = 0.5,
                    dither: Image.Dither = Image.Dither.NONE, harden: bool = True) -> Image.Image:
    """Returns what `image` will actually look like once quantized to the
    panel's palette."""
    quantized = quantize_for_panel(image, saturation=saturation, dither=dither, harden=harden)
    return quantized.convert("RGB")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit("Usage: python scripts/panel_sim.py <input.png> <output.png> [saturation]")
    in_path, out_path = sys.argv[1], sys.argv[2]
    saturation = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
    img = Image.open(in_path)
    simulate_panel(img, saturation).save(out_path)
    print(f"Simulated panel output ({saturation=}) saved to {out_path}")
