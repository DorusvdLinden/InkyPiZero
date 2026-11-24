"""Deterministic coverage for the forecast card's vertical budget
(widgets/forecast.py's compute_card_layout, docs/changes.md entry 61) -
not part of the app. Draws real cards into a blank image and inspects the
text actually drawn (spying on ImageDraw.text). No network/hardware needed.

Covers, for forecast_days 1-14 x dry / rainy (1-digit, 2-digit, <1mm):
1. Every piece of text stays inside the card (before entry 61 the
   day-label/high-low text ran past the card bottom at 5 days or fewer).
2. Text pieces never overlap each other (mm text vs day label/high-low).
3. The mm text uses the same size as the day label wherever the card is
   wide enough (before, it shrank below it at under 5 days).
4. 7 days (the default) keeps exactly the old geometry: 42px icon, 15px
   bold text, day label at card top + 52.
5. No moon-phase text is drawn any more (removed in entry 61).
6. An existing settings file that still has show_moon_phase loads fine
   (the key is ignored), and forecast_days above 14 is rejected (falls
   back to the default) since Open-Meteo can't deliver it.

Run after any change to widgets/forecast.py or layout.forecast_card - see
CLAUDE.md.
"""

import os
import sys

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)
os.chdir(REPO_DIR)

from PIL import Image, ImageDraw

import layout
from weather_data import DayForecast
from widgets import forecast as fw
from widgets.icons import AssetStore

ASSETS = AssetStore(os.path.join(REPO_DIR, "assets", "icons"), os.path.join(REPO_DIR, "assets", "fonts"),
                    font_family="bitter")

DAYS = {
    "dry": DayForecast("wo", "022d", 10, -4, 0.0, False, (0, 0, 0)),
    "rain_1digit": DayForecast("do", "09d", 8, 0, 5.0, True, (0, 0, 0)),
    "rain_2digit": DayForecast("vr", "09d", 10, -4, 20.0, True, (0, 0, 0)),
    "rain_decimal": DayForecast("za", "51d", 7, 2, 0.4, True, (0, 0, 0)),
}


def _draw(region, day):
    """Returns [(text, bbox, font_size)] for everything drawn on one card."""
    image = Image.new("RGB", (800, 480), "white")
    drawn = []
    orig_text = ImageDraw.ImageDraw.text

    def spy_text(self, xy, text, *a, **k):
        font, anchor = k.get("font"), k.get("anchor")
        drawn.append((text, self.textbbox(xy, text, font=font, anchor=anchor), font.size))
        return orig_text(self, xy, text, *a, **k)

    ImageDraw.ImageDraw.text = spy_text
    try:
        fw.draw_forecast_card(image, region, day, ASSETS, (0, 0, 0))
    finally:
        ImageDraw.ImageDraw.text = orig_text
    return drawn


def _overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def test_text_inside_card_and_no_overlap():
    problems = []
    for count in range(1, 15):
        region = layout.forecast_card(0, count)
        inner = (region.x + 2, region.y + 2, region.right - 2, region.bottom - 2)
        for name, day in DAYS.items():
            drawn = _draw(region, day)
            for text, box, _ in drawn:
                if box[0] < inner[0] or box[1] < inner[1] or box[2] > inner[2] or box[3] > inner[3]:
                    problems.append(f"{count}d {name}: {text!r} {box} outside {inner}")
            for i in range(len(drawn)):
                for j in range(i + 1, len(drawn)):
                    if _overlap(drawn[i][1], drawn[j][1]):
                        problems.append(f"{count}d {name}: {drawn[i][0]!r} overlaps {drawn[j][0]!r}")
    if problems:
        print("      " + "\n      ".join(problems[:10]))
        return False
    return True


def test_mm_text_matches_bold_size_where_wide_enough():
    problems = []
    for count in range(1, 11):  # above ~10 days the card width legitimately binds
        region = layout.forecast_card(0, count)
        drawn = _draw(region, DAYS["rain_1digit"])
        sizes = {text: size for text, _, size in drawn}
        if "mm" not in sizes or sizes["mm"] != sizes["do"]:
            problems.append(f"{count}d: mm size {sizes.get('mm')} vs day label {sizes.get('do')}")
    if problems:
        print("      " + "; ".join(problems))
        return False
    return True


def test_default_7_days_geometry_unchanged():
    region = layout.forecast_card(0, 7)
    card = fw.compute_card_layout(region, ASSETS, "wo", "10° / -4°")
    got = (card.icon_size, card.bold_size, card.temps_y - region.y)
    if got != (42, 15, 52):
        print(f"      expected (icon 42, bold 15, temps_y +52), got {got}")
        return False
    return True


def test_no_moon_phase_text():
    for count in (5, 7, 10):
        drawn = _draw(layout.forecast_card(0, count), DAYS["dry"])
        if any(text.endswith("%") for text, _, _ in drawn):
            print(f"      {count}d: found a percentage (moon phase?) in {[t for t, _, _ in drawn]}")
            return False
    return True


def test_old_settings_file_still_loads():
    import json
    import tempfile
    import settings_store
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "settings.json")
        with open(path, "w") as f:
            json.dump({"show_moon_phase": True, "forecast_days": 15, "graph_icon_step": 3}, f)
        orig = settings_store.STATE_PATH
        settings_store.STATE_PATH = path
        try:
            cfg = settings_store.load_config()
        finally:
            settings_store.STATE_PATH = orig
    if cfg.graph_icon_step != 3 or cfg.forecast_days != 7 or hasattr(cfg, "show_moon_phase"):
        print(f"      got graph_icon_step={cfg.graph_icon_step}, forecast_days={cfg.forecast_days}, "
              f"show_moon_phase present={hasattr(cfg, 'show_moon_phase')}")
        return False
    if not settings_store.FIELD_VALIDATORS["forecast_days"](14) or settings_store.FIELD_VALIDATORS["forecast_days"](15):
        print("      forecast_days validator should accept 14 and reject 15")
        return False
    return True


TESTS = [
    test_text_inside_card_and_no_overlap,
    test_mm_text_matches_bold_size_where_wide_enough,
    test_default_7_days_geometry_unchanged,
    test_no_moon_phase_text,
    test_old_settings_file_still_loads,
]


def main():
    results = []
    for test in TESTS:
        try:
            ok = test()
        except Exception as e:
            ok = False
            print(f"FAIL  {test.__name__:55s} raised {e!r}")
        else:
            print(f"{'OK' if ok else 'FAIL':6s}{test.__name__}")
        results.append(ok)
    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
