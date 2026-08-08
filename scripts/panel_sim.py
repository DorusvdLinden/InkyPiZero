"""Dev-time only: simulates what an image will actually look like on the real
Inky Impression 7.3" (AC073TC1A, 7-color ACeP) panel, without needing a
hardware round-trip. Not part of the running app.

The `inky` library's own `set_image()` does two things Windows/--mock-output
renders never show:
  1. Blends a SATURATED_PALETTE (real ink colors) and DESATURATED_PALETTE
     (paper-white-shifted) 50/50 by default (`saturation=0.5`, see
     display/inky_driver.py) to get its actual 7-colour palette.
  2. Quantizes the RGB render down to that palette with Floyd-Steinberg
     dithering (`image.im.convert("P", True, palette_image.im)`).

This reimplements both steps with plain Pillow (`Image.quantize(palette=...,
dither=Image.FLOYDSTEINBERG)` is the documented equivalent of `im.convert`
with the dither flag set) so any render can be previewed as it will actually
appear on the physical panel.

Palette source: pimoroni/inky, inky/inky_ac073tc1a.py (DESATURATED_PALETTE /
SATURATED_PALETTE / _palette_blend), mirrored in widgets/palette.py which
this reuses so the two can't drift apart.
"""

import os
import sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from widgets.palette import native_colors


def simulate_panel(image: Image.Image, saturation: float = 0.5) -> Image.Image:
    """Returns what `image` will actually look like once quantized+dithered
    to the panel's palette - same algorithm the real `inky` driver runs."""
    palette = list(native_colors(saturation).values())
    palette_image = Image.new("P", (1, 1))
    flat = [c for rgb in palette for c in rgb]
    palette_image.putpalette(flat + [0, 0, 0] * (256 - len(palette)))
    quantized = image.convert("RGB").quantize(palette=palette_image, dither=Image.FLOYDSTEINBERG)
    return quantized.convert("RGB")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit("Usage: python scripts/panel_sim.py <input.png> <output.png> [saturation]")
    in_path, out_path = sys.argv[1], sys.argv[2]
    saturation = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
    img = Image.open(in_path)
    simulate_panel(img, saturation).save(out_path)
    print(f"Simulated panel output ({saturation=}) saved to {out_path}")
