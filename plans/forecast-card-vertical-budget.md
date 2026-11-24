# Forecast card: remove the moon phase, fit the text to the card

Status: draft, not confirmed. Covers the three open "Forecast cards"
items in TODO.md, which share one root cause. **Decision 2026-11-24:
remove the moon phase from the cards entirely** (icon, % and the
`show_moon_phase` setting). The comparison renders that led to it are
in `mock_display_output/forecast_card_budget/moon_options/`.

## Context

`widgets/forecast.py`'s `draw_forecast_card` places its rows
independently, and nothing checks that they fit the fixed 95px card
(`layout.FORECAST_ROW.h`):

- icon: `icon_size = min(w * 0.85, h * 0.45)`, top at `y + 6`
- day label + high/low: two lines at `bold_size = max(10, int(w * 0.15))`,
  width-derived only, no shrink-to-fit
- moon row (when `show_moon_phase`): pinned to `bottom - 18`, regardless
  of where the text above ends

Measured 2026-11-24 (line boxes, card-relative y; card is 95px tall,
moon row starts at 77):

| forecast_days | card w | icon | bold_size | temps bottom |
|---|---|---|---|---|
| 1 | 800 | 42 | 120 | 294 |
| 3 | 258 | 42 | 38 | 130 |
| 5 | 150 | 42 | 22 | 98 |
| 7 (default) | 104 | 42 | 15 | 84 |
| 8 | 89 | 42 | 13 | 80 |
| 10 | 69 | 42 | 10 | 74 |
| 14 | 46 | 39 | 10 | 71 |

So:
- **Moon overlap** happens at the default 7 days and up to 8. Removing
  the moon solves it.
- **Text overflow**: at 5 days or fewer, the temps text runs past the
  card bottom (moon or not).
- **mm-text mismatch**: the mm text shrinks below `bold_size` at under 5
  days only because `bold_size` itself is too big for the card. Once
  `bold_size` respects the card height, the two match again.

Also found: `settings_store` accepts any positive `forecast_days`, but
`fetch_snapshot` requests `forecast_days + 1` days and Open-Meteo's
forecast endpoint caps at 16 days, so values above 15 fail the fetch.

## Approach

**1. Remove the moon phase**
- `widgets/forecast.py`: drop the moon block and the `show_moon`
  parameter. `canvas.py`: stop passing it.
- `weather_data.py`: drop `moon_phase_pct` / `moon_icon_key` from
  `DayForecast`, plus the moon calculation, `get_moon_phase_name`,
  `get_moon_phase_icon_key` and the `from astral import moon` import.
- `install/requirements.txt`: remove `astral` (only used for the moon).
- Settings: remove `show_moon_phase` from `config.py`,
  `settings_store.py` (validator), `web/routes.py` and
  `web/templates/settings.html`. Check that a saved settings file on the
  Pi that still contains `show_moon_phase` loads without an error
  (ignored, not rejected). If not, make the loader drop unknown keys.
- **Out of scope, unchanged:** the night icons under the chart and in
  the current-conditions block (`01n` clear night moon, `022n`
  moon + cloud, chosen by `map_weather_code_to_icon` when `is_day == 0`).
  They are separate from the phase icons and stay as they are, including
  `01n` in `widgets/icons.py`'s `MOON_ICON_KEYS` size padding.
- **Keep** the moon PNGs in `assets/icons/` and their entries in
  `scripts/generate_icons.py` (generated artifacts are never deleted).
  `docs/icons.md` marks them as unused since this change.

**2. Fit the text to the card.** A pure function in
`widgets/forecast.py`,
`compute_card_layout(region, assets, day_label, temps_text) -> CardLayout`
(`icon_size`, `bold_size`, `temps_y`):
1. Fixed costs: top padding 6, bottom padding 4, gap 4 between icon and
   text.
2. Text size: the largest size up to the current width formula
   (`w * 0.15`) where both lines fit the card width and two lines still
   leave the icon at least 24px. Floor of 10px, as today.
3. Icon: the height that's left, capped by `w * 0.85` and today's
   `h * 0.45`, so cards that fit today keep exactly today's sizes (7
   days stays pixel-identical apart from the moon going away).

**3. The mm-rain text** keeps `_fit_stacked_lines` unchanged and gets
`bold_size` / `icon_size` from `CardLayout`.

**4. `forecast_days` 1-15**: `_valid_forecast_days` in
`settings_store.py`, `max="15"` on the web input, with the reason in a
comment.

## Documentation updates

- `docs/settings.md`: remove `show_moon_phase` (field table, web UI,
  buttons if mentioned); the "matches at forecast_days 5 through 10"
  paragraph (~line 411) becomes "matches at every forecast_days"; the
  `forecast_days` row gets the 1-15 range.
- `docs/icons.md`: moon icons unused.
- README: features list and install dependencies (astral).
- `docs/attribution.md`: drop astral if it's listed.
- `docs/changes.md`: new entry; mark the entry that added the moon
  phase as superseded by it.
- `TODO.md`: check off the three Forecast-card items.
- Sweep: grep `moon`, `show_moon`, `astral`, `bold_size`.

## Testing

- New `scripts/test_forecast_card_layout.py` (no network): for
  `forecast_days` 1-15 × dry/rainy (1-digit and 2-digit mm), assert
  that the rows don't overlap, everything stays inside the card, the mm
  text matches `bold_size` wherever it isn't width-bound, and the
  layout at 7 days matches today's geometry.
- A settings-load check with an old settings file that still contains
  `show_moon_phase`.
- Renders to `mock_display_output/forecast_card_budget/`: days 1, 3, 5,
  7, 10, 15.
- Standing suite per CLAUDE.md: 14 locations × 3 modes, precip, pollen,
  palette and freshness.
- On the Pi: restart the web and button services (settings code
  changed), force a refresh and check the panel.

## Files touched

`widgets/forecast.py`, `canvas.py`, `weather_data.py`, `config.py`,
`settings_store.py`, `web/routes.py`, `web/templates/settings.html`,
`install/requirements.txt`, docs (settings, icons, changes, README,
attribution), `TODO.md`, new `scripts/test_forecast_card_layout.py`.
