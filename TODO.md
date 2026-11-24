# pi_weather_display - known issues & ideas

- **InkyPiZero**: weather-only e-ink display on a Raspberry Pi with a Pimoroni Inky Impression panel, drawn with Pillow: current weather, hourly chart, forecast, air quality and pollen.
- Status (2026-11-24): built; Nov batch (rounding, rain zero, wind unit, forecast cards, black moon icons, fewer refreshes) on feature/nov-2026-batch, deployed to the Pi, not merged.
- Open: half-cloudy icon choice; tiny mm decimal at 10+ days; hourly icon timezone bug for non-local locations.
- Next: measure refreshes/day on the Pi; merge the batch when approved.
- Details: README.md, docs/settings.md.

Running list of things found during development/testing that aren't fixed yet.
Add to this whenever something rough turns up; check items off (don't delete
them) once fixed. Grouped by area, open items first in each group. See also
`docs/settings.md`, `docs/icons.md`, and `docs/changes.md` for the broader
reference docs this list feeds into.

## Icons

- [ ] Decide whether `022d-new.png`/`022n-new.png` (committed 2026-08-15,
  `c385e7b`) should replace the current `022d`/`022n` "half cloudy"
  composite. Compared both pairs at actual runtime sizes (102px
  current-conditions, 42px forecast card, 30px hourly strip) - see
  `mock_display_output/icon_compare_022_sizes.png` and
  `icon_compare_022_old_vs_new.png`. The `-new` versions scale the cloud
  up and overlap roughly half the sun/moon (vs. just clipping the corner
  in the current version), reading as a more cohesive "cloud in front of
  sun" glyph at small sizes, at the cost of less sun/moon visibility.
  Leaning toward swapping in `-new`, but left as a judgment call pending
  user sign-off rather than done unilaterally.

## Forecast cards

- [x] With `show_moon_phase=True` and a wide rain amount (e.g. a 2-digit
  mm value), the moon-phase percentage row at the bottom of the card can
  visually overlap the day-name/high-low-temp text above it. Confirmed
  pre-existing (not a regression from the 2026-08-15 mm-stacking change
  that found it - reproduced against the pre-change code too via
  `git stash`), found during that change's fresh-context review, unrelated
  to it. Neither `temps_y`'s two text lines nor `moon_y` account for each
  other's actual height when both are shown.
- [x] The mm-rain text's bold size (`widgets/forecast.py`'s `bold_size`,
  shared with the day-label/temps font since 2026-08-15) only actually
  *matches* the day-label/temps size at `forecast_days` 5 through 10 -
  below 5, `icon_size` caps out independently of card width
  (`region.h`-bound, not `region.w`-bound) while `bold_size` keeps
  growing with the wider card, so the mm-text's fixed vertical budget
  above `temps_y` stops growing with it and the text shrinks below
  `bold_size` well before running out of horizontal room; above 10,
  `available_width` becomes the binding constraint instead and the text
  shrinks or omits itself, same as it always has. Not fixed as part of
  that change (would need reworking the card's vertical budget, a bigger
  scope than a font-size/style match) - found via fresh-context review,
  confirmed via direct measurement across `forecast_days` 1-17. (A
  related formula bug - the height check was off by half a line-height,
  needlessly shrinking text even within `icon_size`'s real vertical
  budget - *was* fixed as part of that change, since it was a
  self-contained arithmetic error rather than the architectural gap this
  item describes; it's what widened the matching band from 7-10 to 5-10.)
- [x] Related, pre-existing, unrelated to any 2026-08-15 change: the
  day-label/high-low-temp text itself (`font_bold` in
  `widgets/forecast.py`, `bold_size = max(10, int(region.w * 0.15))`) has
  no shrink-to-fit at all, unlike every other piece of forecast-card
  text - at a very low `forecast_days` (e.g. `1`, unbounded by
  `settings_store` validation), `region.w` approaches `FORECAST_ROW.w`
  (800px) and `bold_size` grows to ~120px inside a fixed 95px-tall card
  row, overflowing badly. Found via fresh-context review while auditing
  the mm-rain sizing change above, not caused by it.
- Fixed 2026-11-24 (docs/changes.md entry 61): the three items above -
  the moon phase is gone from the cards, and one vertical budget
  (`compute_card_layout`) keeps the text inside the card and the mm text
  at the day-label size up to 10 days.
- [ ] At 10+ days the mm text's decimal point is nearly invisible at the
  small size ("0.2 mm" reads as "02 mm" on the render). Pre-existing,
  seen in the entry-61 renders.
- [ ] `forecast_days` max is 14 because the model blend's 16th day comes
  back empty; if `OPEN_METEO_MODELS_PARAM` changes, recheck
  `settings_store.MAX_FORECAST_DAYS`.

## Chart

- [x] Header said "-1°" while the chart's temperature line stayed at 0
  (22 Nov photo): three different rounding rules for the same data. Fixed
  2026-11-24 - one `round_half_up` rule, chart plots unrounded temps
  (docs/changes.md entry 58).
- [x] Rain axis "0" floated partway up the chart in gridlines mode, with
  a bar under every dry hour (10 Nov photo). Fixed 2026-11-24 - the axis
  bottom snaps down to a gridline (docs/changes.md entry 59).

- [ ] Pre-existing, found 2026-11-24 (not from the Nov batch - identical on
  `main`): for a location whose timezone differs from the machine's own
  (e.g. Tokyo in `scripts/test_locations.py` run on a Europe/Amsterdam
  PC), the hourly strip's day/night icons and sunrise/sunset markers are
  shifted by the timezone difference. Open-Meteo returns naive local
  times (`timezone=auto`) and `datetime.fromisoformat(...).astimezone(tz)`
  treats a naive time as the *machine's* local time. No effect on the Pi
  (configured and system timezone are both Europe/Amsterdam).

## Display refresh

- [x] The panel refreshed ~33 times a day (66 in 48h, incl. 2-5 an hour at
  night), each a full flashing refresh. Fixed 2026-11-24: weather groups,
  `refresh_temp_delta` 2, stale timer 120 min (docs/changes.md entry 63).
- [ ] Measure refreshes per day from the Pi's journal a few days after
  deploying entry 63 (baseline 66 / 48h; expected ~10-14 a day).

## Settings

- [x] Add a `wind_speed_unit` setting (m/s vs Beaufort) for the "Wind"
  data point, following the `rain_axis_format` setting's pattern. Full
  implementation plan written to `plans/wind-speed-unit-setting.md`
  (2026-08-31). Built 2026-11-24 together with whole-m/s rounding and the
  plain "UV-index" label (docs/changes.md entry 60).
