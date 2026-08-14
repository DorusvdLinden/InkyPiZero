"""Central color palette for every widget. Every role here is derived from
the Inky Impression 7.3" (AC073TC1A, 7-colour ACeP) panel's own native ink
colors, so nothing dithers unexpectedly once quantized to hardware - the
panel can only ever show black/white/green/blue/red/yellow/orange (see
`native_colors()`), and any authored color that isn't an exact match for one
of those gets Floyd-Steinberg dithered into a speckled mix of its two
nearest neighbours by `InkyDriver`/`inky.set_image()`. That's fine for
something meant to look like a soft blend, but for flat icon fills, chart
lines, and gauge dials it just reads as noise.

`native_colors()` must be computed at the same `saturation` the display is
actually driven at (`DisplayConfig.inky_saturation`) for its colors to
render perfectly flat - the shared `PALETTE` singleton below is kept in
sync with whatever the current config specifies via `set_saturation()`,
called from canvas.py's `WeatherCanvas.__init__`/setup_screen.py's
`render_setup_screen` (the app's two actual rendering entry points), not
hardcoded here. See scripts/panel_sim.py to preview any render as it will
actually look on the physical panel, and scripts/color_options.py for
side-by-side alternatives at other saturations.
"""

# Panel's native palette at full ink saturation vs. fully paper-shifted -
# see pimoroni/inky's inky_ac073tc1a.py (DESATURATED_PALETTE / SATURATED_PALETTE).
_DESATURATED = {
    "black": (0, 0, 0), "white": (255, 255, 255), "green": (0, 255, 0),
    "blue": (0, 0, 255), "red": (255, 0, 0), "yellow": (255, 255, 0), "orange": (255, 140, 0),
}
_SATURATED = {
    "black": (0, 0, 0), "white": (217, 242, 255), "green": (3, 124, 76),
    "blue": (27, 46, 198), "red": (245, 80, 34), "yellow": (255, 255, 68), "orange": (239, 121, 44),
}


def native_colors(saturation: float = 0.5) -> dict[str, tuple[int, int, int]]:
    """The panel's actual achievable flat colors at `saturation` - must
    match `DisplayConfig.inky_saturation` for these to render with zero
    dithering."""
    return {
        name: tuple(round(s * saturation + d * (1.0 - saturation)) for s, d in zip(_SATURATED[name], _DESATURATED[name]))
        for name in _SATURATED
    }


class Palette:
    """Named color roles used across widgets/, all built from
    `native_colors()` so every role is always an exact panel palette
    match at the given saturation."""

    def __init__(self, saturation: float = 0.5):
        self.saturation = saturation
        c = native_colors(saturation)

        # icons (scripts/generate_icons.py)
        self.sun = c["orange"]
        self.moon = c["yellow"]
        self.cloud = c["blue"]
        self.fog = c["black"]
        self.storm = c["black"]
        self.humidity_drop = c["blue"]
        # solid interior of the cloud in the half-cloudy composites
        # (generate_icons.py) - matches config.background_color's white so
        # it reads as "the same paper showing through", not a distinct fill
        self.cloud_interior = c["white"]

        # chart (widgets/chart.py)
        self.chart_warm = c["orange"]
        self.chart_cool = c["blue"]
        self.chart_zero_line = c["black"]

        # forecast cards (widgets/forecast.py) - card_border is currently
        # unused by forecast cards themselves (each card's border color is
        # resolved from weather_quality.toml instead, see
        # weather_data._quality_tier_and_color), kept in case something
        # else wants a neutral border later.
        self.card_border = c["black"]

        # header (canvas.py) - was a soft dark gray (51,51,51) for visual
        # hierarchy vs. the main text, but the panel has no native gray, so
        # that dithered into speckle on a small font; flattened to black.
        self.text_muted = c["black"]

        # wind compass (widgets/gauge.py)
        self.wind_dial = c["black"]
        self.wind_needle = c["red"]
        self.wind_hub = c["white"]

        # pressure gauge (widgets/gauge.py)
        self.pressure_dial = c["blue"]
        self.pressure_rain_icon = c["blue"]
        self.pressure_cloud_icon = c["black"]
        self.pressure_sun_icon = c["orange"]
        self.pressure_needle = c["black"]
        self.pressure_needle_outline = c["white"]

        # AQI gauge (widgets/gauge.py) - band order matches COMBINED_TIERS's
        # own Goed->Zeer slecht ramp (weather_data.py). Only 4 rungs
        # (green/yellow/orange/red) fit before running into the display's
        # fixed 7-color limit, so the 5th/worst band reuses black - same
        # precedent as uv_extreme just below.
        self.aqi_band_low = c["green"]
        self.aqi_band_moderate = c["yellow"]
        self.aqi_band_high = c["orange"]
        self.aqi_band_very_high = c["red"]
        self.aqi_band_extreme = c["black"]
        self.aqi_needle = c["black"]
        # A black-on-black needle would vanish when pointing into the new
        # extreme band above, so it gets the same needle+outline treatment
        # pressure_needle/pressure_needle_outline already use.
        self.aqi_needle_outline = c["white"]

        # UV icon (weather_data.get_uv_color / widgets/gauge.render_uv_icon) -
        # discrete per the same tiers get_uv_rating_nl already shows as text
        # (Laag/Matig/Hoog/Zeer hoog/Extreem), rather than a continuous
        # gradient that would dither between them.
        self.uv_low = c["green"]
        self.uv_moderate = c["yellow"]
        self.uv_high = c["orange"]
        self.uv_very_high = c["red"]
        self.uv_extreme = c["black"]

    def set_saturation(self, saturation: float):
        """Mutates this instance in place so the shared `PALETTE` singleton
        stays the same object - anything that did `from widgets.palette
        import PALETTE` keeps working after the swap."""
        self.__dict__.update(Palette(saturation).__dict__)


PALETTE = Palette(saturation=0.0)  # matches DisplayConfig's own default;
# kept in sync with whatever's actually configured via set_saturation()
# (see canvas.py/setup_screen.py) - this initial value is only ever used
# before the first real render, or by dev tools that never call sync.
