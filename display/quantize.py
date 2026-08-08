"""Prepares a rendered canvas for the Inky panel's fixed 7-colour palette.
Shared by the real hardware path (inky_driver.py) and the local preview
tool (scripts/panel_sim.py) so the two can't drift apart.

Uses nearest-color quantization (no dithering) instead of the `inky`
library's default Floyd-Steinberg. Error-diffusion dithering is built for
photos - letting a *region* average out to the right tone by scattering
error across pixels - which is the wrong tool for small line art (chart
lines, icon outlines, gauge dials): each antialiased edge pixel doesn't
exactly match a palette entry, and diffusing that error into neighbors
turns a thin stroke into visible speckle/gaps even at an otherwise exact
color match.

Nearest-color alone isn't enough, though: an antialiased black-on-white
edge blends through every shade of neutral gray, and on this specific
7-colour palette a mid-gray's *nearest* color by Euclidean RGB distance is
actually orange, not black or white - orange sits more centrally in the
color cube than any of the near-corner colors (black/white/red/green/
blue/yellow all have at least one channel pinned to 0 or 255). Floyd-
Steinberg was masking this by diffusing the "wrong" choice away as noise;
nearest-color exposes it as a solid, systematic orange fringe around every
piece of text, chart axis, and black icon. `harden_neutral_pixels()` snaps
near-gray pixels to pure black/white *before* quantizing, removing the
ambiguity at the source - colored content (which was never near-neutral)
is untouched.
"""

from PIL import Image, ImageChops

from widgets.palette import native_colors


def harden_neutral_pixels(image: Image.Image, threshold: int = 128, tolerance: int = 20) -> Image.Image:
    """Snaps antialiased near-gray pixels (R~=G~=B, within `tolerance`) to
    pure black or white based on `threshold` luminance. Leaves colored
    pixels (icons, chart lines, gauges) untouched."""
    image = image.convert("RGB")
    r, g, b = image.split()
    max_c = ImageChops.lighter(ImageChops.lighter(r, g), b)
    min_c = ImageChops.darker(ImageChops.darker(r, g), b)
    diff = ImageChops.subtract(max_c, min_c)
    is_gray_mask = diff.point(lambda v: 255 if v <= tolerance else 0)
    hardened_l = image.convert("L").point(lambda v: 0 if v < threshold else 255)
    result = image.copy()
    result.paste(hardened_l.convert("RGB"), (0, 0), is_gray_mask)
    return result


def quantize_for_panel(image: Image.Image, saturation: float = 0.5,
                        dither: Image.Dither = Image.Dither.NONE, harden: bool = True) -> Image.Image:
    """Hardens neutral edges, then quantizes to the panel's native palette.
    Returns a "P"-mode image - passing this directly to `inky.set_image()`
    makes it skip its own internal (always-Floyd-Steinberg) quantization,
    since that only re-quantizes images that aren't already mode "P". The
    palette entries must stay in the exact order `native_colors()` returns
    them (black/white/green/blue/red/yellow/orange) - that's the same
    index order `inky`'s own SATURATED_PALETTE/DESATURATED_PALETTE uses,
    which is what makes the resulting palette indices mean the right ink
    color once `inky` reads them back out of the "P" image's raw pixel
    values.

    `dither`/`harden` are only exposed for A/B comparison (see
    scripts/panel_sim.py) - real hardware output always wants both."""
    prepared = harden_neutral_pixels(image) if harden else image.convert("RGB")
    palette = list(native_colors(saturation).values())
    palette_image = Image.new("P", (1, 1))
    flat = [c for rgb in palette for c in rgb]
    palette_image.putpalette(flat + [0, 0, 0] * (256 - len(palette)))
    return prepared.quantize(palette=palette_image, dither=dither)
