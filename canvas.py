from PIL import Image, ImageDraw

import layout
from config import DisplayConfig
from weather_data import WeatherSnapshot
from widgets import gauge, forecast as forecast_widget, icons as icons_widget
from widgets import chart as chart_widget
from widgets.palette import PALETTE


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))


def _data_point_value_text(dp: dict) -> str:
    value_parts = [dp["direction"]] if dp.get("direction") else []
    value_parts.append(str(dp["measurement"]))
    value_text = " ".join(value_parts)
    if dp.get("unit"):
        value_text += f"{dp.get('unit_separator', ' ')}{dp['unit']}"
    return value_text


# "compact" screen mode (button D) drops these two, keeping wind/humidity/uv/aqi.
COMPACT_KINDS = {"wind", "humidity", "uv", "aqi"}


class WeatherCanvas:
    def __init__(self, assets: icons_widget.AssetStore, config: DisplayConfig, screen_mode: str = "original"):
        # Keeps every PALETTE.* color an exact panel-palette match at
        # whatever saturation this config actually specifies - PALETTE is
        # a shared singleton that otherwise stays frozen at its own
        # hardcoded default forever (see widgets/palette.py).
        PALETTE.set_saturation(config.inky_saturation)
        self.assets = assets
        self.config = config
        self.screen_mode = screen_mode
        self.bg = _hex_to_rgb(config.background_color)
        self.text_color = _hex_to_rgb(config.text_color)

    def render(self, data: WeatherSnapshot) -> Image.Image:
        image = Image.new("RGB", layout.CANVAS_SIZE, self.bg)
        draw = ImageDraw.Draw(image)

        self._draw_header(draw, data)
        self._draw_current_conditions(image, draw, data)
        self._draw_data_points(image, draw, data)
        self._draw_chart(image, data)
        self._draw_forecast_row(image, data)
        return layout.inset_with_margin(image, self.bg)

    def _draw_header(self, draw, data: WeatherSnapshot):
        font_refresh = self.assets.font("bold", 14)
        date_text = data.current_date
        if data.location:
            date_text += f", {data.location}"
        # data.location is API-sourced (Nominatim) and can come back in a
        # non-Latin script neither Jost nor Bitter has glyphs for (e.g. a
        # Japanese city name) - unlike every other label in the app, which
        # is always Dutch/numeric, so only this call site needs fallback.
        self.assets.draw_text_with_fallback(
            draw, (layout.HEADER.x, layout.HEADER.bottom), date_text, "bold", 22, self.text_color, anchor="lb")
        draw.text((layout.HEADER.right - 4, layout.HEADER.y), f"Laatste update: {data.last_refresh_time}",
                   font=font_refresh, fill=PALETTE.text_muted, anchor="ra")

    def _draw_current_conditions(self, image, draw, data: WeatherSnapshot):
        region = layout.CURRENT_TEMPERATURE
        icon_size = int(region.h * 0.62)
        icon = self.assets.icon(data.current_icon_key, (icon_size, icon_size))
        icon_x = region.x + int(region.w * 0.22)
        icon_y = region.y + int(region.h * 0.12)
        if icon:
            image.paste(icon, (icon_x - icon_size // 2, icon_y), icon)

        text_cx = region.x + int(region.w * 0.68)
        font_temp = self.assets.font("bold", 64)
        font_unit = self.assets.font("bold", 24)
        font_small = self.assets.font("bold", 19)

        temp_str = str(data.current_temp)
        temp_y = region.y + int(region.h * 0.42)
        draw.text((text_cx, temp_y), temp_str, font=font_temp, fill=self.text_color, anchor="mm")
        temp_w = draw.textlength(temp_str, font=font_temp)
        draw.text((text_cx + temp_w / 2 + 4, temp_y - 22), data.temp_unit, font=font_unit, fill=self.text_color, anchor="lm")

        # Bigger than the original 15px, and pushed further down toward the
        # region's own bottom edge (region.bottom, not the chart below it -
        # CHART_AREA.y is fixed independently in layout.py) to reclaim the
        # gap that used to sit unused between these two lines and the chart.
        draw.text((text_cx, temp_y + 40), f"Gevoelstemp. {data.feels_like}°", font=font_small, fill=self.text_color, anchor="mm")
        draw.text((text_cx, temp_y + 74),
                   f"{data.last_night_low}° / {data.day_high}° / {data.next_night_low}°",
                   font=font_small, fill=self.text_color, anchor="mm")

    def _draw_data_points(self, image, draw, data: WeatherSnapshot):
        if self.screen_mode == "compact":
            self._draw_data_points_compact(image, draw, data)
            return
        for i, dp in enumerate(data.data_points):
            cell = layout.data_point_cell(i)
            icon_w = int(cell.w * layout.DATA_POINT_ICON_FRACTION)
            icon_box = layout.Region(cell.x, cell.y, icon_w, cell.h)
            self._draw_data_point_icon(image, icon_box, dp)

            text_x = cell.x + icon_w + 8
            max_width = cell.right - text_x - 4
            value_text = _data_point_value_text(dp)
            # Shrinks to fit instead of a fixed 18px, same as compact mode's
            # cells - different font families have different metrics at the
            # same point size ("Kwaliteit & Pollen" clipped in Bitter, which
            # is wider than Jost, before this).
            font_label = self._fit_font(dp["label"], "normal", 18, max_width)
            font_value = self._fit_font(value_text, "bold", 18, max_width)
            label_y = cell.y + int(cell.h * 0.28)
            value_y = cell.y + int(cell.h * 0.68)
            draw.text((text_x, label_y), dp["label"], font=font_label, fill=self.text_color, anchor="lm")
            draw.text((text_x, value_y), value_text, font=font_value, fill=self.text_color, anchor="lm")

    def _draw_data_points_compact(self, image, draw, data: WeatherSnapshot):
        """"compact" screen mode (button D) - 4 details (wind/humidity/uv/aqi -
        "aqi" is the combined "Kwaliteit & Pollen" data point, see
        weather_data._combine_aqi_pollen_tier) instead of 6, bigger fonts in
        the reclaimed space, same icon-then-stacked-text arrangement as the
        original 6-detail grid just in 2x2 cells."""
        points = [dp for dp in data.data_points if dp["kind"] in COMPACT_KINDS]
        cells = [layout.data_point_cell_2x2(i) for i in range(len(points))]

        for dp, cell in zip(points, cells):
            self._draw_compact_cell(image, draw, cell, dp)

    def _fit_font(self, text: str, weight: str, max_size: int, max_width: float, min_size: int = 12):
        """Shrinks in 2px steps until text fits max_width, floor min_size -
        needed since compact mode's cells are a fixed pixel width but data
        point labels vary a lot in length ("UV-index 1-12" vs "Kwaliteit &
        Pollen") and draw.text doesn't wrap/clip on its own."""
        for size in range(max_size, min_size - 1, -2):
            font = self.assets.font(weight, size)
            if font.getlength(text) <= max_width:
                return font
        return self.assets.font(weight, min_size)

    def _draw_compact_cell(self, image, draw, cell: layout.Region, dp: dict):
        icon_w = int(cell.w * 0.32)
        icon_box = layout.Region(cell.x, cell.y, icon_w, cell.h)
        self._draw_data_point_icon(image, icon_box, dp)

        text_x = cell.x + icon_w + 10
        max_width = cell.right - text_x - 4
        value_text = _data_point_value_text(dp)
        font_label = self._fit_font(dp["label"], "normal", 24, max_width)
        font_value = self._fit_font(value_text, "bold", 24, max_width)
        label_y = cell.y + int(cell.h * 0.36)
        value_y = cell.y + int(cell.h * 0.68)
        draw.text((text_x, label_y), dp["label"], font=font_label, fill=self.text_color, anchor="lm")
        draw.text((text_x, value_y), value_text, font=font_value, fill=self.text_color, anchor="lm")

    def _draw_data_point_icon(self, image, box: layout.Region, dp: dict):
        kind = dp["kind"]
        if kind == "wind":
            gauge_img = gauge.render_wind_compass(dp["rotation"])
        elif kind == "pressure":
            gauge_img = gauge.render_pressure_gauge(dp["gauge_rotation"])
        elif kind == "uv":
            gauge_img = gauge.render_uv_icon(dp["uv_color"], dp["uv_beams"])
        elif kind == "aqi":
            gauge_img = gauge.render_aqi_gauge(dp["aqi_rotation"])
        elif kind == "humidity":
            icons_widget.draw_humidity_drops(image, box, self.assets, dp["drop_count"])
            return
        elif kind == "visibility":
            scale = 0.55
            w, h = max(1, int(box.w * scale)), max(1, int(box.h * scale))
            icon = self.assets.icon("visibility", (w, h))
            if icon:
                image.paste(icon, (box.x + (box.w - w) // 2, box.y + (box.h - h) // 2), icon)
            return
        else:
            return

        scale = min(box.w / gauge_img.width, box.h / gauge_img.height)
        target_size = (max(1, int(gauge_img.width * scale)), max(1, int(gauge_img.height * scale)))
        resized = gauge_img.resize(target_size, Image.LANCZOS)
        paste_x = box.x + (box.w - resized.width) // 2
        paste_y = box.y + (box.h - resized.height) // 2
        image.paste(resized, (paste_x, paste_y), resized)

    def _draw_chart(self, image, data: WeatherSnapshot):
        temp_unit_label = data.temp_unit.replace("°", "")
        chart_widget.render_chart(
            image, layout.CHART_AREA, data.hourly, data.sun_events, self.text_color,
            lambda key, size: self.assets.icon(key, size), self.config.graph_icon_step,
            self.assets.font("normal", 13), self.assets.font("bold", 14), self.assets.font("bold", 18),
            temp_unit_label, data.precip_label,
            # "compact" gets the gridlines chart style too - only "original"
            # keeps the actual-day min/max dashed lines.
            show_temp_gridlines=(self.screen_mode in ("gridlines", "compact")),
            rain_axis_format=self.config.rain_axis_format,
        )

    def _draw_forecast_row(self, image, data: WeatherSnapshot):
        count = len(data.daily)
        if count == 0:
            return
        for i, day in enumerate(data.daily):
            region = layout.forecast_card(i, count)
            forecast_widget.draw_forecast_card(image, region, day, self.assets, self.text_color, self.config.show_moon_phase)
